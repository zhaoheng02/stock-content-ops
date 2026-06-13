"""Ingest X posts collected by the Airtap cloud phone into normalized records.

Airtap returns a JSON object with `profiles` and `posts`. This module:
- normalizes each post into a flat record,
- computes a stable content hash for dedupe,
- parses the human-visible publish time (including Chinese forms like
  "下午10:52 · 2026年6月12日") into an ISO timestamp when possible.

The records are storage-ready for the Supabase `source_posts` table.
"""

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional


SHANGHAI_TZ = timezone(timedelta(hours=8))


def content_hash(author_handle: str, text: str, post_id: str = "") -> str:
    basis = "\n".join([
        (author_handle or "").strip().lower().lstrip("@"),
        (post_id or "").strip(),
        (text or "").strip(),
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def parse_publish_time(raw: Optional[str]) -> Optional[str]:
    """Parse a human/absolute publish time into ISO 8601, else None.

    Handles:
    - ISO 8601 already (returned as-is, normalized).
    - Chinese form: "下午10:52 · 2026年6月12日" / "上午9:05 2026年6月12日".
    """
    if not raw:
        return None
    text = str(raw).strip()
    if _looks_relative_time(text):
        return None

    # Try ISO first.
    iso_candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate).isoformat()
    except ValueError:
        pass

    # Chinese absolute form.
    cn = re.search(
        r"(上午|下午|凌晨|晚上)?\s*(\d{1,2}):(\d{2}).*?(\d{4})年(\d{1,2})月(\d{1,2})日",
        text,
    )
    if cn:
        meridiem, hh, mm, year, month, day = cn.groups()
        hour = int(hh)
        minute = int(mm)
        if meridiem in ("下午", "晚上") and hour < 12:
            hour += 12
        if meridiem in ("凌晨", "上午") and hour == 12:
            hour = 0
        dt = datetime(int(year), int(month), int(day), hour, minute, tzinfo=SHANGHAI_TZ)
        return dt.isoformat()

    # English "MMM D, YYYY" with optional time, best-effort.
    en = re.search(r"([A-Z][a-z]{2,8})\s+(\d{1,2}),\s*(\d{4})", text)
    if en:
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                dt = datetime.strptime(f"{en.group(1)} {en.group(2)}, {en.group(3)}", fmt)
                return dt.replace(tzinfo=SHANGHAI_TZ).isoformat()
            except ValueError:
                continue
    return None


def _looks_relative_time(text: str) -> bool:
    lowered = text.strip().lower()
    return bool(re.fullmatch(
        r"(\d+\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks|mo|month|months|y|yr|yrs|year|years)|\d+[smhdw])\s*(ago)?",
        lowered,
    ))


def _avatar_for(handle: str, profiles: list) -> dict:
    handle_l = (handle or "").lower().lstrip("@")
    for p in profiles or []:
        if str(p.get("author_handle", "")).lower().lstrip("@") == handle_l:
            return p
    return {}


def _coerce_flat_payload(payload: dict) -> dict:
    """Accept either the flat {profiles, posts} shape or the nested
    {accounts:[{...profile..., posts:[...]}]} shape Airtap returns, and
    return the flat shape with normalized post keys.
    """
    if "accounts" in payload and "posts" not in payload:
        profiles = []
        posts = []
        for acct in payload.get("accounts", []) or []:
            handle = acct.get("handle") or acct.get("author_handle")
            profiles.append({
                "author_handle": handle,
                "author_name": acct.get("display_name") or acct.get("author_name"),
                "avatar_url": acct.get("avatar_url"),
                "bio": acct.get("bio"),
                "profile_url": acct.get("profile_url") or (f"https://x.com/{handle}" if handle else None),
            })
            for post in acct.get("posts", []) or []:
                posts.append(_coerce_post(post, handle, acct.get("display_name")))
        return {
            "collected_at": payload.get("collected_at"),
            "profiles": profiles,
            "posts": posts,
        }
    # already flat; still coerce post keys
    posts = [_coerce_post(p, p.get("author_handle"), p.get("author_name")) for p in payload.get("posts", []) or []]
    return {
        "collected_at": payload.get("collected_at"),
        "profiles": payload.get("profiles", []) or [],
        "posts": posts,
    }


def _coerce_post(post: dict, handle: Optional[str], name: Optional[str]) -> dict:
    return {
        "id": post.get("id"),
        "author_handle": post.get("author_handle") or handle,
        "author_name": post.get("author_name") or name,
        "published_at": post.get("published_at") or post.get("published"),
        "text": post.get("text", ""),
        "url": post.get("url"),
        "image_urls": post.get("image_urls") or post.get("images") or [],
        "video_urls": post.get("video_urls") or post.get("videos") or [],
        "link_cards": post.get("link_cards") or [],
        "quote": post.get("quote"),
        "metrics": post.get("metrics") or {},
        "media_error": post.get("media_error"),
        "is_reply": post.get("is_reply"),
        "reply_to": post.get("reply_to"),
    }


def normalize_airtap_payload(payload: dict, source_id: str = "x", run_id: str = "",
                             profiles_by_handle: Optional[dict] = None) -> List[dict]:
    """Turn an Airtap result payload into storage-ready post records.

    Replies are excluded. Avatars/profile fields are backfilled from
    profiles_by_handle (the one-time monitored_accounts profile data) since the
    collection prompt no longer fetches avatars.
    """
    payload = _coerce_flat_payload(payload)
    profiles = payload.get("profiles", []) or []
    posts = payload.get("posts", []) or []
    collected_at = payload.get("collected_at") or datetime.now(SHANGHAI_TZ).isoformat()
    profiles_by_handle = profiles_by_handle or {}

    records: List[dict] = []
    seen_hashes = set()
    for post in posts:
        if _is_reply(post):
            continue
        handle = str(post.get("author_handle", "")).strip().lstrip("@")
        text = str(post.get("text", "") or "")
        post_id = str(post.get("id", "") or "")
        chash = content_hash(handle, text, post_id)
        if chash in seen_hashes:
            continue
        seen_hashes.add(chash)

        prof = _avatar_for(handle, profiles)
        stored = profiles_by_handle.get(handle.lower(), {})
        url = post.get("url") or (
            f"https://x.com/{handle}/status/{post_id}" if handle and post_id else None
        )
        published_raw = post.get("published_at")
        published_at = parse_publish_time(published_raw)
        if not published_at:
            continue
        records.append({
            "content_hash": chash,
            "source_id": source_id,
            "run_id": run_id or None,
            "platform": "x",
            "post_id": post_id or None,
            "author_handle": handle,
            "author_name": post.get("author_name") or prof.get("author_name") or stored.get("author_name"),
            "author_avatar_url": prof.get("avatar_url") or stored.get("avatar_url"),
            "author_bio": prof.get("bio") or stored.get("bio"),
            "text": text,
            "url": url,
            "published_at": published_at,
            "published_at_raw": published_raw,
            "image_urls": post.get("image_urls", []) or [],
            "video_urls": post.get("video_urls", []) or [],
            "link_cards": post.get("link_cards", []) or [],
            "quote": post.get("quote"),
            "metrics": post.get("metrics", {}) or {},
            "media_error": post.get("media_error"),
            "collected_at": collected_at,
            "raw": post,
        })
    return records


def _is_reply(post: dict) -> bool:
    if post.get("is_reply") is True:
        return True
    reply_to = post.get("reply_to")
    if reply_to:
        return True
    # Heuristic: a leading "@handle" mention typically marks a reply.
    text = str(post.get("text", "") or "").lstrip()
    return text.startswith("@")


def extract_profiles(payload: dict) -> List[dict]:
    """Pull profile records out of an Airtap profile-lookup payload."""
    payload = _coerce_flat_payload(payload)
    out = []
    for p in payload.get("profiles", []) or []:
        handle = str(p.get("author_handle", "")).strip().lstrip("@")
        if not handle:
            continue
        out.append({
            "handle": handle,
            "author_name": p.get("author_name"),
            "avatar_url": p.get("avatar_url"),
            "bio": p.get("bio"),
            "profile_url": p.get("profile_url") or f"https://x.com/{handle}",
        })
    return out


def extract_airtap_json(text: str) -> Optional[dict]:
    """Find and parse the JSON object embedded in an Airtap final message."""
    if not text:
        return None
    # Strip code fences.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    # Greedy: first { to last } that parses.
    start = text.find("{")
    end = text.rfind("}")
    while start != -1 and end != -1 and end > start:
        chunk = text[start:end + 1]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            end = text.rfind("}", start, end)
    return None
