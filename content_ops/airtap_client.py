"""Zero-dependency Airtap client.

Drives the Airtap cloud phone over its HTTP API using only the stdlib, so it
runs inside Vercel Python serverless functions (no `requests`/`dotenv`).

Auth: reads AIRTAP_PERSONAL_ACCESS_TOKEN from the environment (set as a Vercel
project env var in production; never committed).

Used to collect X posts: create a task with the collection prompt, poll until
it finishes, then pull the JSON object out of the agent's final message.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional


BASE_URL = os.environ.get("AIRTAP_BASE_URL", "https://airtap.ai/cortex/api")
TOKEN_ENV_VAR = "AIRTAP_PERSONAL_ACCESS_TOKEN"
DEFAULT_RECEIVER_ID = "cloud"
DEFAULT_MODEL_ID = "airtap-1.0"
FINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}
WAITING_STATES = {
    "WAITING_FOR_USER_INPUT",
    "WAITING_FOR_USER_INTERVENTION",
    "WAITING_FOR_USER_CONTINUE",
}
STOP_STATES = FINAL_STATES | WAITING_STATES


class AirtapError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AirtapError(
            f"{TOKEN_ENV_VAR} is not set; configure it as a Vercel env var"
        )
    return token


def _request(path: str, payload: dict, timeout: int = 60) -> dict:
    url = f"{BASE_URL}{path}"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "x-airtap-pilot-client-type": "pilot-agent",
        "x-airtap-pilot-client-name": "overseas-relay",
    }
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        raise AirtapError(f"Airtap API {path} failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise AirtapError(f"Airtap API {path} unreachable: {error}") from error
    return json.loads(raw) if raw else {}


def create_task(message_text: str, receiver_id: str = DEFAULT_RECEIVER_ID,
                model_id: Optional[str] = DEFAULT_MODEL_ID) -> str:
    payload = {
        "receiverId": receiver_id,
        "userMessage": {"type": "user", "parts": [{"type": "text", "text": message_text}]},
    }
    if model_id:
        payload["modelId"] = model_id
    result = _request("/task/v1/taskCreate", payload)
    task_id = result.get("taskId") or result.get("task", {}).get("taskId")
    if not task_id:
        raise AirtapError(f"Airtap taskCreate returned no taskId: {json.dumps(result)[:300]}")
    return task_id


def get_details(task_id: str) -> dict:
    return _request("/task/v1/taskGetDetails", {"taskId": task_id})


def poll_until_done(task_id: str, interval_secs: float = 8.0, max_wait_secs: float = 280.0) -> dict:
    deadline = time.monotonic() + max_wait_secs
    while True:
        details = get_details(task_id)
        state = details.get("taskState")
        if isinstance(state, str) and state in STOP_STATES:
            details["_finalState"] = state
            return details
        if time.monotonic() >= deadline:
            details["_finalState"] = "TIMEOUT"
            return details
        time.sleep(interval_secs)


def latest_agent_text(details: dict) -> str:
    messages = details.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("type") != "agent":
            continue
        parts = message.get("parts")
        if not isinstance(parts, list):
            continue
        texts = [
            p.get("text", "")
            for p in parts
            if isinstance(p, dict) and p.get("type") == "text" and p.get("text")
        ]
        if texts:
            return "\n\n".join(texts)
    return ""


def build_x_profile_prompt(handles) -> str:
    """One-time prompt: fetch each account's profile name, avatar URL and bio.

    Run once when accounts are added; post collection never re-fetches avatars.
    """
    handles = [str(h).lstrip("@").strip() for h in handles if str(h).strip()]
    bullet = "\n".join(f"- {h}" for h in handles)
    return f"""Profile lookup task on the Airtap cloud phone. For each X (Twitter) account below, open its profile page https://x.com/<handle> and read its display name, avatar image URL (a https://pbs.twimg.com/profile_images/... URL), and bio.

Accounts:
{bullet}

Do NOT collect posts. Only profile metadata.

Return ONE JSON object in your final message using exactly these snake_case keys:

{{
  "collected_at": "<ISO 8601 time in Asia/Shanghai>",
  "profiles": [
    {{"author_handle": "<handle>", "author_name": "<display name>", "avatar_url": "https://pbs.twimg.com/profile_images/....jpg", "bio": "<bio or empty>", "profile_url": "https://x.com/<handle>"}}
  ]
}}

Rules:
- One profile object per account, in the same order.
- avatar_url must be a direct https://pbs.twimg.com/profile_images/... URL.
- Do NOT post the JSON anywhere; just return it in your final message.
- Never expose any token or secret."""


def build_x_collection_prompt(handles, posts_per_account: int = 3, since_by_handle=None) -> str:
    """Build the X collection task prompt.

    Two modes per account:
    - Cold start (handle not in since_by_handle): take the latest
      `posts_per_account` ORIGINAL posts.
    - Incremental (handle has a `since` timestamp): take every ORIGINAL post
      strictly newer than that time (could be many, could be zero).

    Replies are always excluded. Avatars are NOT fetched here.
    """
    handles = [str(h).lstrip("@").strip() for h in handles if str(h).strip()]
    since_by_handle = since_by_handle or {}
    lines = []
    search_urls = []
    for h in handles:
        since = since_by_handle.get(h) or since_by_handle.get(h.lower())
        if since:
            lines.append(f"- {h}: collect every ORIGINAL post published strictly after {since} (newest first). If none are newer, return none for this account.")
        else:
            lines.append(f"- {h}: cold start — collect the latest {posts_per_account} ORIGINAL posts (newest first).")
        search_urls.append(f"- https://x.com/search?q=from%3A{h}&src=typed_query&f=live")
    per_account = "\n".join(lines)
    urls = "\n".join(search_urls)
    return f"""X (Twitter) data collection task on the Airtap cloud phone. Log in to X if needed using the app/x.com already set up on this cloud phone. Do not ask the human to log in unless X shows a hard login wall you cannot pass.

Per-account instructions:
{per_account}

For each account, open this live search URL directly (newest first):
{urls}

IMPORTANT — only collect ORIGINAL posts the account itself published. EXCLUDE replies, EXCLUDE pure retweets, EXCLUDE pinned ads. Quote-posts authored by the account are allowed. A reply is any post that starts with "@someone" replying in a thread, or that X shows as "Replying to ...". Skip those.

For EVERY collected post, extract raw data only. Do NOT translate, rewrite, summarize, shorten, or infer the post body. Output exact values you can see. Do NOT fetch profile avatars here.

Return ONE JSON object in your final message using exactly these snake_case keys:

{{
  "collected_at": "<ISO 8601 time in Asia/Shanghai>",
  "posts": [
    {{"id": "<tweet id digits>", "author_handle": "<handle>", "author_name": "<display name>", "published_at": "<absolute time, ISO 8601 with timezone if possible, e.g. 2026-06-12T22:52:00+08:00>", "text": "<full exact post body, no edits>", "url": "https://x.com/<handle>/status/<id>", "image_urls": [], "video_urls": [], "link_cards": [], "quote": null, "metrics": {{"likes": null, "reposts": null, "replies": null, "views": null}}, "is_reply": false}}
  ]
}}

Rules:
- published_at MUST be an absolute timestamp (date + time), never a relative form like "5h" or "2 days ago". Open the post permalink/hover to get the absolute time if needed. Include timezone.
- If id and handle are visible, set url to https://x.com/<handle>/status/<id>.
- If a post has media, image_urls/video_urls must not be silently empty; use direct https://pbs.twimg.com/media/... URLs. If you truly cannot, add a "media_error" field on that post.
- metrics: fill what you can read; use null otherwise.
- Set is_reply:true only if you mistakenly included a reply; prefer to exclude replies entirely.
- Do NOT post the JSON anywhere; just return it in your final message.
- Never expose any token or secret.

If X shows a hard login wall, captcha, or verification you cannot pass, STOP and report exactly what blocked you and on which account."""


def collect_via_airtap(message_text: str, receiver_id: str = DEFAULT_RECEIVER_ID,
                       model_id: Optional[str] = DEFAULT_MODEL_ID,
                       max_wait_secs: float = 280.0) -> dict:
    """Run one collection task end-to-end and return the parsed JSON payload.

    Raises AirtapError if the task fails, times out, or returns no JSON.
    """
    from .x_ingest import extract_airtap_json

    task_id = create_task(message_text, receiver_id=receiver_id, model_id=model_id)
    details = poll_until_done(task_id, max_wait_secs=max_wait_secs)
    state = details.get("_finalState")
    text = latest_agent_text(details)
    if state == "COMPLETED":
        payload = extract_airtap_json(text)
        if payload is None:
            raise AirtapError("Airtap task completed but returned no parseable JSON result")
        payload.setdefault("_task_id", task_id)
        return payload
    raise AirtapError(f"Airtap task did not complete (state={state}): {text[:200]}")
