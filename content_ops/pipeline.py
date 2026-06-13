from typing import Optional

from .ai_review import AIReviewer
from .generator import generate_assets
from .models import CaseCandidate, PipelineResult
from .providers import PostProvider
from .scoring import score_post
from .settings import PipelineSettings


def run_pipeline(
    provider: PostProvider,
    settings: PipelineSettings,
    reviewer: Optional[AIReviewer] = None,
) -> PipelineResult:
    scanned = list(provider.fetch_posts())
    accepted = []

    for post in scanned:
        if reviewer:
            decision = reviewer.review(post)
            score, reasons = decision.score, decision.reasons
        else:
            score, reasons = score_post(post)
        if score < settings.min_score:
            continue
        accepted.append(
            CaseCandidate(
                source_id=post.id,
                account=post.account,
                source_url=post.url,
                score=score,
                score_reasons=reasons,
                assets=generate_assets(post, settings.persona),
            )
        )

    accepted.sort(key=lambda case: case.score, reverse=True)
    limited = accepted[: settings.daily_limit]
    return PipelineResult(
        cases=limited,
        scanned_count=len(scanned),
        accepted_count=len(limited),
    )
