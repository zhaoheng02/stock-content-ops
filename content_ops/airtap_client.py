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


def build_x_collection_prompt(handles, posts_per_account: int = 3) -> str:
    """Build the X collection task prompt for a set of handles."""
    handles = [str(h).lstrip("@").strip() for h in handles if str(h).strip()]
    bullet_handles = "\n".join(f"- {h}" for h in handles)
    search_urls = "\n".join(
        f"- https://x.com/search?q=from%3A{h}&src=typed_query&f=live" for h in handles
    )
    total = len(handles) * posts_per_account
    return f"""Cold-start X (Twitter) data collection task. Use the Airtap cloud phone. Log in to X if needed using the X/Twitter app or x.com already set up on this cloud phone. Do not ask the human to log in unless X shows a hard login/verification wall you cannot pass.

Goal: collect the latest {posts_per_account} posts from EACH of these {len(handles)} accounts ({total} posts total on a full run):
{bullet_handles}

For each account, open this live search URL directly and read the most recent original posts (newest first):
{search_urls}

Take the {posts_per_account} most recent posts per account regardless of date. Skip pure retweets and pinned ads if obvious, but keep normal posts and quote-posts.

For EVERY post, extract raw data only. Do NOT translate, rewrite, summarize, shorten, or infer the post body. Output exact values you can see.

Also capture each account's PROFILE/AVATAR image: open the account profile (https://x.com/<handle>) and read the avatar image URL (a https://pbs.twimg.com/profile_images/... URL). Include the account display name and bio if visible.

Return the final result as ONE JSON object in your final message, using exactly these snake_case keys:

{{
  "collected_at": "<ISO 8601 time in Asia/Shanghai>",
  "profiles": [
    {{"author_handle": "<handle>", "author_name": "<display name>", "avatar_url": "https://pbs.twimg.com/profile_images/....jpg", "bio": "<bio or empty>", "profile_url": "https://x.com/<handle>"}}
  ],
  "posts": [
    {{"id": "<tweet id digits>", "author_name": "<display name>", "author_handle": "<handle>", "published_at": "<exact post time as shown, plus absolute form if visible>", "text": "<full exact post body, no edits>", "url": "https://x.com/<handle>/status/<id>", "image_urls": ["https://pbs.twimg.com/media/....jpg"], "video_urls": [], "link_cards": [], "quote": null, "metrics": {{"likes": null, "reposts": null, "replies": null, "views": null}}}}
  ]
}}

Rules:
- If id and handle are visible, set url to https://x.com/<handle>/status/<id>.
- published_at: record the exact human-visible time shown on the post.
- If a post visibly has media, image_urls/video_urls must not be silently empty; use direct https://pbs.twimg.com/media/... URLs. If you truly cannot get a real media URL, add a "media_error" field on that post.
- metrics: fill what you can read; use null for any you cannot see.
- Do NOT post the JSON to any backend or external API. Just return the JSON in your final message.
- Never expose any token or secret in your report.

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
