import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, List, Optional, Protocol

from .models import SourcePost


DEFAULT_X_API_BASE_URL = "https://api.x.com/2"


class JsonTransport(Protocol):
    def get_json(self, url: str, bearer_token: str) -> dict:
        ...


class UrlLibJsonTransport:
    def get_json(self, url: str, bearer_token: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {bearer_token}"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


class XApiPostProvider:
    def __init__(
        self,
        handles: Iterable[str],
        bearer_token: str,
        transport: Optional[JsonTransport] = None,
        max_results_per_account: int = 5,
        api_base_url: str = DEFAULT_X_API_BASE_URL,
    ):
        self.handles = [handle.strip().lstrip("@") for handle in handles if handle.strip()]
        self.bearer_token = bearer_token
        self.transport = transport or UrlLibJsonTransport()
        self.max_results_per_account = max(5, min(100, max_results_per_account))
        self.api_base_url = api_base_url.rstrip("/")

    @classmethod
    def from_env(cls, handles: Iterable[str], max_results_per_account: int = 5) -> "XApiPostProvider":
        token = os.environ.get("X_BEARER_TOKEN")
        if not token:
            raise RuntimeError("X_BEARER_TOKEN is required for collect-x")
        return cls(
            handles=handles,
            bearer_token=token,
            max_results_per_account=max_results_per_account,
            api_base_url=os.environ.get("X_API_BASE_URL", DEFAULT_X_API_BASE_URL),
        )

    def fetch_posts(self) -> Iterable[SourcePost]:
        posts: List[SourcePost] = []
        for handle in self.handles:
            user = self._lookup_user(handle)
            posts.extend(self._fetch_user_posts(user_id=user["id"], username=user["username"]))
        return posts

    def _lookup_user(self, handle: str) -> dict:
        encoded = urllib.parse.quote(handle)
        url = f"{self.api_base_url}/users/by/username/{encoded}?user.fields=id,username"
        payload = self.transport.get_json(url, self.bearer_token)
        return payload["data"]

    def _fetch_user_posts(self, user_id: str, username: str) -> List[SourcePost]:
        query = urllib.parse.urlencode(
            {
                "max_results": self.max_results_per_account,
                "exclude": "retweets,replies",
                "tweet.fields": "created_at,public_metrics,lang",
            }
        )
        url = f"{self.api_base_url}/users/{urllib.parse.quote(user_id)}/tweets?{query}"
        payload = self.transport.get_json(url, self.bearer_token)
        posts = []
        for tweet in payload.get("data", []):
            metrics = tweet.get("public_metrics") or {}
            tweet_id = str(tweet["id"])
            posts.append(
                SourcePost(
                    id=tweet_id,
                    account=username,
                    text=str(tweet.get("text") or ""),
                    url=f"https://x.com/{username}/status/{tweet_id}",
                    metrics={
                        "likes": int(metrics.get("like_count", 0)),
                        "reposts": int(metrics.get("retweet_count", 0)),
                        "replies": int(metrics.get("reply_count", 0)),
                    },
                )
            )
        return posts


def write_posts_json(posts: Iterable[SourcePost], path: str) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "id": post.id,
            "account": post.account,
            "text": post.text,
            "url": post.url,
            "metrics": dict(post.metrics),
        }
        for post in posts
    ]
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)
