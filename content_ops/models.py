from dataclasses import dataclass, field
from typing import Dict, List, Mapping


@dataclass(frozen=True)
class SourcePost:
    id: str
    account: str
    text: str
    url: str
    metrics: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ContentAsset:
    platform: str
    title: str
    body: str
    persona_policy: str


@dataclass(frozen=True)
class CaseCandidate:
    source_id: str
    account: str
    source_url: str
    score: int
    score_reasons: List[str]
    assets: Dict[str, ContentAsset]


@dataclass(frozen=True)
class PipelineResult:
    cases: List[CaseCandidate]
    scanned_count: int
    accepted_count: int

