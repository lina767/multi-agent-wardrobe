"""Scientific evidence registry — maps operational rules to citations."""

from dataclasses import dataclass
from typing import Literal

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    title: str
    citation_short: str
    principle: str
    scope: str
    confidence: Confidence


_REGISTRY: dict[str, EvidenceRecord] = {
    "enclothed_cognition": EvidenceRecord(
        evidence_id="enclothed_cognition",
        title="Enclothed cognition",
        citation_short="Adam & Galinsky (2012); Horton et al. meta-analytic update (2023)",
        principle="Clothing symbolic meaning affects psychological processes; formal/professional cues can align with performance goals.",
        scope="Meeting/business context + appropriately formal garments",
        confidence="medium",
    ),
    "choice_overload_paradox": EvidenceRecord(
        evidence_id="choice_overload_paradox",
        title="Choice overload / demotivation",
        citation_short="Schwartz (2004); Iyengar & Lepper (2000)",
        principle="Many similar options increase decision cost; curated shortlists improve decision quality and satisfaction.",
        scope="Presentation of ranked Top-3 outfits only",
        confidence="high",
    ),
    "decision_fatigue": EvidenceRecord(
        evidence_id="decision_fatigue",
        title="Ego depletion / willpower budgeting",
        citation_short="Baumeister & Tierney (2011)",
        principle="Pre-filtering wardrobe combinations reduces sequential micro-decisions early in the day.",
        scope="Automated constraint filtering before ranking",
        confidence="medium",
    ),
    "color_harmony_itten": EvidenceRecord(
        evidence_id="color_harmony_itten",
        title="Systematic color relationships",
        citation_short="Itten (1961); Jackson (1980) applied seasonal palettes",
        principle="Coordinated palettes reduce clash; neutrals bridge complex combinations.",
        scope="Color-family harmony and palette bias alignment",
        confidence="medium",
    ),
    "capsule_wardrobe_creativity": EvidenceRecord(
        evidence_id="capsule_wardrobe_creativity",
        title="Capsule wardrobe & everyday creativity",
        citation_short="MDPI Sustainability (2022) capsule wardrobe creativity",
        principle="Smaller versatile sets can support sustained outfit variety with lower cognitive load.",
        scope="Reward high mixability (neutrals + layering)",
        confidence="medium",
    ),
    "cognitive_dissonance": EvidenceRecord(
        evidence_id="cognitive_dissonance",
        title="Consistency in self-presentation",
        citation_short="Festinger (1957)",
        principle="Outfits strongly mismatched to context create discomfort; align context dress code with selection.",
        scope="Context agent hard constraints vs style boldness",
        confidence="low",
    ),
    "agentic_reco_pipeline": EvidenceRecord(
        evidence_id="agentic_reco_pipeline",
        title="Agentic personalized fashion recommendation",
        citation_short="AMMR Pipeline (2025, arXiv)",
        principle="Decomposed specialist signals improve multi-objective outfit matching vs single monolithic model.",
        scope="Multi-agent partial scores + orchestrator merge",
        confidence="medium",
    ),
}


def get_registry() -> dict[str, EvidenceRecord]:
    return _REGISTRY


def get_evidence(eid: str) -> EvidenceRecord | None:
    return _REGISTRY.get(eid)
