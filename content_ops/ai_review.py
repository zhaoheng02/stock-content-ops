import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import List, Protocol

from .models import SourcePost


REVIEW_SYSTEM_PROMPT = """
你是商业案例筛选器，只筛选能转化为中文内容矩阵的海外高价值案例。
评分维度：
1. 是否属于 AI工具、AI创业、AI出海、独立开发、B2B SaaS、健康长寿、财经。
2. 是否有数据、操作步骤、失败/成功原因、定价、增长、产品机制等可验证证据。
3. 是否能转成中文市场的商业启发，而不是单纯观点或情绪。
4. 是否适合后续生成小红书、视频号、公众号、抖音内容。
只返回 JSON：{"score":0-100,"reasons":["..."],"summary":"..."}。
""".strip()


class AIReviewer(Protocol):
    def review(self, post: SourcePost) -> "AIReviewDecision":
        ...


@dataclass(frozen=True)
class AIReviewDecision:
    score: int
    reasons: List[str]
    summary: str


class OpenAIResponsesReviewer:
    def __init__(self, api_key: str, model: str = "gpt-4.1", timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAIResponsesReviewer":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when --use-gpt is enabled")
        return cls(
            api_key=api_key,
            model=os.environ.get("OPENAI_MODEL", "gpt-4.1"),
        )

    def review(self, post: SourcePost) -> AIReviewDecision:
        payload = {
            "model": self.model,
            "input": [
                {"role": "developer", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": build_review_prompt(post)},
            ],
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        return parse_review_json(extract_response_text(response_payload))


def build_review_prompt(post: SourcePost) -> str:
    return (
        f"账号：@{post.account}\n"
        f"链接：{post.url}\n"
        f"互动：{dict(post.metrics)}\n"
        f"内容：{post.text}\n"
        "请判断它是否值得进入今日高价值案例库。"
    )


def parse_review_json(text: str) -> AIReviewDecision:
    cleaned = _extract_json_object(text)
    payload = json.loads(cleaned)
    score = int(payload.get("score", 0))
    reasons = [str(reason) for reason in payload.get("reasons", [])]
    summary = str(payload.get("summary", ""))
    return AIReviewDecision(
        score=max(0, min(100, score)),
        reasons=reasons,
        summary=summary,
    )


def extract_response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        raise ValueError(f"AI review response did not contain JSON: {text[:120]}")
    return match.group(0)
