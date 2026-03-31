"""Rule-based color harmony against palette bias and neutral bridging."""

from app.agents.base import BaseAgent
from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput
from app.domain.enums import ColorFamily
from app.domain.scoring import clamp_score, decision_trace_entry


class ColorAgent(BaseAgent):
    name = "color"

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline_input: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        items = candidate.items
        bias = set(pipeline_input.palette_bias)
        families = [cf for it in items for cf in it.color_families]

        harmony = 0.65
        reasons: list[str] = []
        trace: list = []

        if not families:
            harmony = 0.55
            reasons.append("No color metadata; neutral default harmony.")
        else:
            neutral_count = sum(1 for f in families if f == ColorFamily.NEUTRAL)
            if neutral_count >= len(items):
                harmony = 0.82
                reasons.append("Mostly neutral palette — high coordination.")
            elif bias:
                hits = sum(1 for f in families if f in bias)
                ratio = hits / max(len(families), 1)
                harmony = 0.6 + 0.35 * ratio
                reasons.append(f"Palette bias overlap {ratio:.0%} with declared season/bias.")
            else:
                # Penalize too many competing bold families
                bold = sum(1 for f in families if f == ColorFamily.BOLD)
                if bold >= 3:
                    harmony = 0.52
                    reasons.append("Multiple bold accents — higher clash risk.")
                else:
                    harmony = 0.72
                    reasons.append("Balanced non-bias heuristic harmony.")

        trace.append(
            decision_trace_entry(self.name, "harmony", round(harmony, 3), "Composite color-family harmony score.")
        )
        return AgentEvaluationResult(
            agent_name=self.name,
            partial_scores={"harmony": clamp_score(harmony)},
            reasons=reasons,
            trace=trace,
        )
