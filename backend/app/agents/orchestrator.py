"""Score merger for recommendation pipeline."""

from __future__ import annotations

from typing import Any

from app.domain.entities import AgentEvaluationResult
from app.domain.enums import EventType


class OrchestratorAgent:
    def merge(
        self,
        results: list[AgentEvaluationResult],
        event_type: EventType,
    ) -> tuple[float, dict[str, float], list[str], list[dict[str, Any]], float]:
        partials: dict[str, float] = {}
        reasons: list[str] = []
        trace: list[dict[str, Any]] = []
        for r in results:
            partials.update(r.partial_scores)
            reasons.extend(r.reasons)
            trace.extend(r.trace)

        weights = {
            "harmony": 0.25,
            "style_fit": 0.25,
            "wardrobe_coherence": 0.2,
            "context_fit": 0.3 if event_type == EventType.MEETING else 0.2,
        }
        if event_type == EventType.MEETING:
            reasons.append("Meeting context gives extra weight to context fit.")

        total_weight = 0.0
        score_sum = 0.0
        for key, weight in weights.items():
            if key in partials:
                score_sum += partials[key] * weight
                total_weight += weight
        total = (score_sum / total_weight) if total_weight > 0 else 0.0

        conf = 0.0
        if partials:
            values = list(partials.values())
            conf = max(values) - min(values)
        partials["orchestrator_confidence"] = round(conf, 4)
        return max(0.0, min(1.0, total)), partials, reasons, trace, conf
