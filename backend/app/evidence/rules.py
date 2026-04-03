"""Evidence-based score adjustments and tagged rationales."""

from dataclasses import dataclass
from typing import Any

from app.api.schemas import ContextInput
from app.domain.entities import WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType
from app.domain.scoring import clamp_score
from app.evidence.registry import get_evidence


@dataclass
class EvidenceAdjustment:
    evidence_id: str
    citation_short: str
    delta: float
    rationale: str


class EvidenceRuleEngine:
    """Applies small bounded adjustments derived from evidence principles."""

    MAX_ABS_DELTA = 0.12

    def apply(
        self,
        base_score: float,
        context: ContextInput,
        items: list[WardrobeItemDTO],
        partials: dict[str, float],
    ) -> tuple[float, list[EvidenceAdjustment]]:
        adjustments: list[EvidenceAdjustment] = []
        s = base_score

        # Enclothed cognition: business meeting + adequate formality
        if context.event_type == EventType.MEETING:
            max_formality = max((it.formality for it in items), key=lambda x: _formality_rank(x), default=None)
            if max_formality and _formality_rank(max_formality) >= _formality_rank(DresscodeLevel.SMART_CASUAL):
                rec = get_evidence("enclothed_cognition")
                if rec:
                    d = self._bound(0.04)
                    s += d
                    adjustments.append(
                        EvidenceAdjustment(
                            evidence_id=rec.evidence_id,
                            citation_short=rec.citation_short,
                            delta=d,
                            rationale="Meeting context: outfit meets smart-casual+ formality — aligns with enclothed-cognition cues.",
                        )
                    )

        # Color harmony / neutrals
        neutrals = sum(1 for it in items if ColorFamily.NEUTRAL in it.color_families)
        if neutrals >= 1 and len(items) >= 2:
            rec = get_evidence("color_harmony_itten")
            if rec:
                d = self._bound(0.03)
                s += d
                adjustments.append(
                    EvidenceAdjustment(
                        evidence_id=rec.evidence_id,
                        citation_short=rec.citation_short,
                        delta=d,
                        rationale="Neutral anchor piece improves palette coordination per systematic color-harmony heuristics.",
                    )
                )

        # Capsule / versatility: multiple items tagged classic or minimalist
        tags = {t.lower() for it in items for t in it.style_tags}
        if tags & {"classic", "minimalist", "versatile", "basic"}:
            rec = get_evidence("capsule_wardrobe_creativity")
            if rec:
                d = self._bound(0.03)
                s += d
                adjustments.append(
                    EvidenceAdjustment(
                        evidence_id=rec.evidence_id,
                        citation_short=rec.citation_short,
                        delta=d,
                        rationale="Versatile style tags support high mixability (capsule-style wardrobe principle).",
                    )
                )

        # Choice overload: systems presents top-3 — tag when base pipeline produced clear separation
        if partials.get("orchestrator_confidence", 0) >= 0.15:
            rec = get_evidence("choice_overload_paradox")
            if rec:
                d = self._bound(0.02)
                s += d
                adjustments.append(
                    EvidenceAdjustment(
                        evidence_id=rec.evidence_id,
                        citation_short=rec.citation_short,
                        delta=d,
                        rationale="Short ranked list reduces choice overload vs exhaustive wardrobe search.",
                    )
                )

        # Decision fatigue / pre-filtering — tag once when context constraints applied
        if context.event_type in (EventType.MEETING, EventType.DATE) or context.dresscode_override:
            rec = get_evidence("decision_fatigue")
            if rec:
                d = self._bound(0.02)
                s += d
                adjustments.append(
                    EvidenceAdjustment(
                        evidence_id=rec.evidence_id,
                        citation_short=rec.citation_short,
                        delta=d,
                        rationale="Context filters pre-apply dress constraints, reducing sequential decision effort.",
                    )
                )

        # Agentic decomposition — always tag (core architecture principle)
        rec = get_evidence("agentic_reco_pipeline")
        if rec:
            d = self._bound(0.02 if len(partials) >= 4 else 0.015)
            s += d
            adjustments.append(
                EvidenceAdjustment(
                    evidence_id=rec.evidence_id,
                    citation_short=rec.citation_short,
                    delta=d,
                    rationale="Specialist agent signals merged before ranking (agentic recommendation pattern).",
                )
            )

        # Cognitive dissonance: strong context mismatch already penalized in agents; small nudge if aligned
        if context.dresscode_override:
            target = context.dresscode_override
            all_match = all(_formality_rank(it.formality) >= _formality_rank(target) - 1 for it in items)
            if all_match:
                rec = get_evidence("cognitive_dissonance")
                if rec:
                    d = self._bound(0.02)
                    s += d
                    adjustments.append(
                        EvidenceAdjustment(
                            evidence_id=rec.evidence_id,
                            citation_short=rec.citation_short,
                            delta=d,
                            rationale="Outfit within overridden dress-code band reduces context-self-presentation tension.",
                        )
                    )

        # Guarantee ≥2 evidence hooks for explainability (choice overload + agentic already common)
        if len(adjustments) < 2:
            rec = get_evidence("choice_overload_paradox")
            if rec and not any(a.evidence_id == rec.evidence_id for a in adjustments):
                d = self._bound(0.02)
                s += d
                adjustments.append(
                    EvidenceAdjustment(
                        evidence_id=rec.evidence_id,
                        citation_short=rec.citation_short,
                        delta=d,
                        rationale="Curated shortlist (Top-3) implements choice-overload mitigation.",
                    )
                )

        return clamp_score(s), adjustments

    def _bound(self, delta: float) -> float:
        if delta > self.MAX_ABS_DELTA:
            return self.MAX_ABS_DELTA
        if delta < -self.MAX_ABS_DELTA:
            return -self.MAX_ABS_DELTA
        return delta


def _formality_rank(f: DresscodeLevel) -> int:
    order = [
        DresscodeLevel.SPORT,
        DresscodeLevel.CASUAL,
        DresscodeLevel.SMART_CASUAL,
        DresscodeLevel.BUSINESS,
        DresscodeLevel.FORMAL,
    ]
    return order.index(f) if f in order else 0


def adjustments_to_trace(adj: list[EvidenceAdjustment]) -> list[dict[str, Any]]:
    return [
        {
            "type": "evidence",
            "evidence_id": a.evidence_id,
            "effect_on_score": a.delta,
            "rationale": a.rationale,
            "citation": a.citation_short,
        }
        for a in adj
    ]
