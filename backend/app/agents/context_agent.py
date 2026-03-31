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
        feels_like = pipeline.context.feels_like_c
        rain_probability = pipeline.context.rain_probability
        uv_index = pipeline.context.uv_index
        wind_speed_kph = pipeline.context.wind_speed_kph
        has_outer = any(it.category.value == "outer" for it in candidate.items)
        has_accessory = any(it.category.value == "accessory" for it in candidate.items)
        score = 0.82
        reasons: list[str] = ["Context fit is acceptable."]
        effective_temp = feels_like if feels_like is not None else temp
        if effective_temp is not None and effective_temp < 8 and not has_outer:
            score = 0.45
            reasons = ["Cold weather without an outer layer."]
        elif effective_temp is not None and effective_temp > 24 and has_outer:
            score = 0.55
            reasons = ["Warm weather with unnecessary outer layer."]

        if rain_probability is not None and rain_probability >= 0.55:
            has_water_resistant = any(
                any(tag in (it.material or "").lower() for tag in ("water", "rain", "nylon", "shell"))
                or any(tag in it.name.lower() for tag in ("rain", "umbrella", "waterproof"))
                for it in candidate.items
            )
            if has_water_resistant:
                score += 0.07
                reasons.append("Rain-aware material choice improves fit.")
            else:
                score -= 0.17
                reasons.append("High rain probability without water-resistant pieces.")

        if uv_index is not None and uv_index >= 6:
            has_uv_accessory = any(
                any(tag in it.name.lower() for tag in ("hat", "cap", "sunglass", "sun"))
                or any(tag in " ".join(it.style_tags).lower() for tag in ("sun", "outdoor"))
                for it in candidate.items
            )
            if has_accessory and has_uv_accessory:
                score += 0.1
                reasons.append("High UV handled with protective accessory.")
            elif not has_accessory:
                score -= 0.12
                reasons.append("High UV without accessory support.")

        if wind_speed_kph is not None and wind_speed_kph >= 30:
            has_wind_risk = any(
                any(tag in it.name.lower() for tag in ("scarf", "flowy", "wide", "maxi"))
                or any(tag in " ".join(it.style_tags).lower() for tag in ("flowy", "oversized"))
                for it in candidate.items
            )
            if has_wind_risk:
                score -= 0.14
                reasons.append("Strong wind conflicts with lightweight or flowy silhouette.")
            else:
                score += 0.05
                reasons.append("Silhouette remains stable in strong wind.")
        return AgentEvaluationResult(
            agent_name="context",
            partial_scores={"context_fit": max(0.0, min(1.0, score))},
            reasons=reasons,
        )

