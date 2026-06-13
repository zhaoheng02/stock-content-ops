import json
from pathlib import Path
from typing import Iterable, List, Protocol

from .models import SourcePost


class PostProvider(Protocol):
    def fetch_posts(self) -> Iterable[SourcePost]:
        ...


class StaticPostProvider:
    def __init__(self, posts: Iterable[dict]):
        self._posts = [normalize_post(post) for post in posts]

    def fetch_posts(self) -> Iterable[SourcePost]:
        return list(self._posts)


class JsonFilePostProvider:
    def __init__(self, path: str):
        self.path = Path(path)

    def fetch_posts(self) -> Iterable[SourcePost]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("posts", [])
        return [normalize_post(post) for post in payload]


def normalize_post(post: dict) -> SourcePost:
    metrics = post.get("metrics") or {}
    return SourcePost(
        id=str(post["id"]),
        account=str(post.get("account") or post.get("username") or "unknown"),
        text=str(post.get("text") or ""),
        url=str(post.get("url") or ""),
        metrics={str(key): int(value) for key, value in metrics.items()},
    )

