import json
import re
from pathlib import Path
from typing import Dict

from .models import PipelineResult


def export_review_queue(result: PipelineResult, out_dir: str, batch_name: str = "batch") -> str:
    root = Path(out_dir)
    drafts_dir = root / "drafts" / _slug(batch_name)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "batch_name": batch_name,
        "scanned_count": result.scanned_count,
        "accepted_count": result.accepted_count,
        "items": [],
    }

    for case in result.cases:
        drafts: Dict[str, str] = {}
        for platform_key, asset in case.assets.items():
            relative = Path("drafts") / _slug(batch_name) / f"{_slug(case.source_id)}-{platform_key}.md"
            draft_path = root / relative
            draft_path.write_text(_render_asset(case.source_url, asset), encoding="utf-8")
            drafts[platform_key] = str(relative)

        manifest["items"].append(
            {
                "source_id": case.source_id,
                "account": case.account,
                "source_url": case.source_url,
                "score": case.score,
                "score_reasons": case.score_reasons,
                "drafts": drafts,
                "status": "needs_review",
            }
        )

    manifest_path = root / f"{_slug(batch_name)}-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(manifest_path)


def _render_asset(source_url: str, asset) -> str:
    return (
        f"# {asset.title}\n\n"
        f"- 平台：{asset.platform}\n"
        f"- 来源：{source_url}\n"
        f"- 人设策略：{asset.persona_policy}\n\n"
        f"{asset.body}\n"
    )


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "item"
