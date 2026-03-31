"""Context: weather, event, mood → soft scores and constraint hints."""

from app.agents.base import BaseAgent
from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput
from app.domain.enums import DresscodeLevel, EventType, WardrobeCategory
from app.domain.scoring import clamp_score, decision_trace_entry


class ContextAgent(BaseAgent):
    name = "context"

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline_input: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        ctx = pipeline_input.context
        reasons: list[str] = []
        trace: list = []
        score = 0.7

        required = _required_formality(ctx.event_type, ctx.dresscode_override)
        min_item_formality = min((it.formality for it in candidate.items), key=_rank_formality)
        if _rank_formality(min_item_formality) < _rank_formality(required) - 1:
            score -= 0.28
            reasons.append(
                f"Weakest piece formality {min_item_formality.value} below context expectation ~{required.value}."
            )
        else:
            reasons.append(f"Formality aligns with context (target {required.value}).")

        # Temperature: cold without outer
        temp = ctx.temperature_c
        if temp is not None and temp < 8.0:
            has_outer = any(it.category == WardrobeCategory.OUTER for it in candidate.items)
            if not has_outer:
                score -= 0.12
                reasons.append("Cold weather heuristic: no outer layer.")
            else:
                score += 0.05
                reasons.append("Cold weather: includes outer layer.")

        # Mood: low energy prefers casual/comfort
        if ctx.mood.value == "low" and ctx.event_type not in (EventType.MEETING,):
            max_f = max((it.formality for it in candidate.items), key=_rank_formality)
            if _rank_formality(max_f) >= _rank_formality(DresscodeLevel.BUSINESS):
                score -= 0.06
                reasons.append("Low mood: heavy formality slightly downweighted for comfort.")

        trace.append(decision_trace_entry(self.name, "context_fit", round(score, 3), "Event + weather + mood fit."))
        return AgentEvaluationResult(
            agent_name=self.name,
            partial_scores={"context_fit": clamp_score(score)},
            reasons=reasons,
            trace=trace,
        )


def _required_formality(event: EventType, override: DresscodeLevel | None) -> DresscodeLevel:
    if override:
        return override
    if event == EventType.MEETING:
        return DresscodeLevel.SMART_CASUAL
    if event == EventType.DATE:
        return DresscodeLevel.SMART_CASUAL
    if event == EventType.HOME:
        return DresscodeLevel.CASUAL
    return DresscodeLevel.CASUAL


def _rank_formality(f: DresscodeLevel) -> int:
    order = [
        DresscodeLevel.CASUAL,
        DresscodeLevel.SMART_CASUAL,
        DresscodeLevel.BUSINESS,
        DresscodeLevel.FORMAL,
    ]
    return order.index(f) if f in order else 0
