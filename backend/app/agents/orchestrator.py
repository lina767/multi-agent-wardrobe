"""Supervisor: merges agent partial scores with conflict-aware weights."""

from app.domain.entities import AgentEvaluationResult
from app.domain.enums import EventType
from app.domain.scoring import clamp_score, decision_trace_entry, merge_partial_scores


class OrchestratorAgent:
    name = "orchestrator"

    def merge(
        self,
        results: list[AgentEvaluationResult],
        event_type: EventType,
    ) -> tuple[float, dict[str, float], list[str], list[dict], float]:
        """
        Returns (total_score, partial_map, reasons, trace, orchestrator_confidence).
        """
        partials: dict[str, float] = {}
        reasons: list[str] = []
        trace: list[dict] = []
        for r in results:
            partials.update(r.partial_scores)
            reasons.extend(r.reasons)
            trace.extend(r.trace)

        weights = self._weights_for_event(event_type)
        total = merge_partial_scores(weights, partials)

        # Conflict resolution narrative
        if event_type == EventType.MEETING:
            reasons.append("Supervisor: meeting context upweights context_fit + formality-related signals.")
        elif event_type == EventType.DATE:
            reasons.append("Supervisor: date context balances style_fit and context_fit.")

        spread = max(partials.values()) - min(partials.values()) if partials else 0.0
        confidence = clamp_score(spread * 1.2 + 0.05)
        partials_out = dict(partials)
        partials_out["orchestrator_confidence"] = confidence

        trace.append(
            decision_trace_entry(
                self.name,
                "weights",
                weights,
                "Event-driven weight map for partial score merge.",
            )
        )
        trace.append(
            decision_trace_entry(
                self.name,
                "total_pre_evidence",
                round(total, 4),
                "Weighted merge before evidence adjustments.",
            )
        )
        return total, partials_out, reasons, trace, confidence

    def _weights_for_event(self, event: EventType) -> dict[str, float]:
        base = {
            "harmony": 1.0,
            "style_fit": 1.0,
            "wardrobe_coherence": 0.9,
            "context_fit": 1.1,
        }
        if event == EventType.MEETING:
            return {**base, "context_fit": 1.45, "style_fit": 0.95, "harmony": 1.0}
        if event == EventType.DATE:
            return {**base, "style_fit": 1.25, "context_fit": 1.05}
        if event == EventType.HOME:
            return {**base, "context_fit": 0.85, "style_fit": 1.05, "wardrobe_coherence": 1.0}
        return base
