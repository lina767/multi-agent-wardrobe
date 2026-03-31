"""Style clustering heuristics from preferences and outfit-history tags."""

from app.agents.base import BaseAgent
from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput
from app.domain.enums import DresscodeLevel, EventType
from app.domain.scoring import clamp_score, decision_trace_entry


class StyleAgent(BaseAgent):
    name = "style"

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline_input: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        prefs = pipeline_input.style_preferences
        hist = {t.lower() for t in pipeline_input.outfit_history_tags}

        item_tags = {t.lower() for it in candidate.items for t in it.style_tags}
        reasons: list[str] = []
        trace: list = []

        score = 0.62

        pref_hits = len(item_tags & {p.lower() for p in prefs.preferred_style_tags})
        if pref_hits:
            score += 0.08 * min(pref_hits, 3)
            reasons.append(f"Matches {pref_hits} preferred style tag(s).")

        avoid = {a.lower() for a in prefs.avoid_style_tags}
        if item_tags & avoid:
            score -= 0.18
            reasons.append("Contains avoided style tags — penalized.")

        hist_overlap = len(item_tags & hist)
        if hist_overlap:
            score += 0.05 * min(hist_overlap, 2)
            reasons.append("Consistent with recent outfit-history tags.")

        # Power outfit / enclothed: meeting + elevated formality
        if pipeline_input.context.event_type == EventType.MEETING:
            max_f = max((it.formality for it in candidate.items), key=_rank_formality)
            if _rank_formality(max_f) >= _rank_formality(DresscodeLevel.SMART_CASUAL):
                boost = 0.04 + 0.06 * prefs.power_outfit_preference
                score += boost
                reasons.append("Meeting context benefits from elevated formality (power-outfit weighting).")

        trace.append(decision_trace_entry(self.name, "style_fit", round(score, 3), "Preference + history overlap."))
        return AgentEvaluationResult(
            agent_name=self.name,
            partial_scores={"style_fit": clamp_score(score)},
            reasons=reasons or ["Default style fit."],
            trace=trace,
        )


def _rank_formality(f: DresscodeLevel) -> int:
    order = [
        DresscodeLevel.CASUAL,
        DresscodeLevel.SMART_CASUAL,
        DresscodeLevel.BUSINESS,
        DresscodeLevel.FORMAL,
    ]
    return order.index(f) if f in order else 0
