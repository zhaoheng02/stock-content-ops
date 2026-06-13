from dataclasses import dataclass


DEFAULT_PERSONA = (
    "统一人设：理性商业拆解者，以证据、机制、行动清单重构海外案例；"
    "避免复制原作者表达。"
)


@dataclass(frozen=True)
class PipelineSettings:
    min_score: int = 70
    daily_limit: int = 20
    persona: str = DEFAULT_PERSONA

