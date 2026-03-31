"""Context aggregation for weather and occasion constraints."""

from __future__ import annotations

from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput
from app.services.weather import WeatherService


class ContextAgent:
    def __init__(self) -> None:
        self.weather = WeatherService()

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        temp = pipeline.context.temperature_c
        has_outer = any(it.category.value == "outer" for it in candidate.items)
        score = 0.82
        reasons: list[str] = ["Context fit is acceptable."]
        if temp is not None and temp < 8 and not has_outer:
            score = 0.45
            reasons = ["Cold weather without an outer layer."]
        elif temp is not None and temp > 24 and has_outer:
            score = 0.55
            reasons = ["Warm weather with unnecessary outer layer."]
        return AgentEvaluationResult(
            agent_name="context",
            partial_scores={"context_fit": score},
            reasons=reasons,
        )

