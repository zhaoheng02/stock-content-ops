from typing import List, Tuple

from .models import SourcePost


DOMAIN_KEYWORDS = {
    "ai": 18,
    "agent": 14,
    "startup": 14,
    "founder": 12,
    "saas": 16,
    "b2b": 14,
    "pricing": 12,
    "onboarding": 12,
    "churn": 12,
    "roi": 10,
    "funnel": 10,
    "trial": 8,
    "automation": 8,
    "longevity": 8,
    "finance": 6,
}

EVIDENCE_KEYWORDS = {
    "%": 12,
    "reduced": 10,
    "grew": 10,
    "benchmark": 10,
    "published": 8,
    "exact": 8,
    "teardown": 8,
    "case": 6,
    "metrics": 6,
}


def score_post(post: SourcePost) -> Tuple[int, List[str]]:
    text = post.text.lower()
    score = 0
    reasons: List[str] = []

    domain_hits = [keyword for keyword in DOMAIN_KEYWORDS if keyword in text]
    if domain_hits:
        domain_score = min(42, sum(DOMAIN_KEYWORDS[keyword] for keyword in domain_hits))
        score += domain_score
        reasons.append("domain_fit")

    evidence_hits = [keyword for keyword in EVIDENCE_KEYWORDS if keyword in text]
    if evidence_hits:
        evidence_score = min(34, sum(EVIDENCE_KEYWORDS[keyword] for keyword in evidence_hits))
        score += evidence_score
        reasons.append("has_evidence")

    engagement = (
        post.metrics.get("likes", 0)
        + post.metrics.get("reposts", 0) * 3
        + post.metrics.get("replies", 0) * 2
    )
    if engagement >= 100:
        score += min(24, engagement // 20)
        reasons.append("market_signal")

    if len(post.text) >= 100:
        score += 8
        reasons.append("enough_context")

    return min(score, 100), reasons

