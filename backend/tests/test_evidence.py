"""Positive/negative tests for evidence rule adjustments."""

from app.api.schemas import ContextInput
from app.domain.entities import WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType, ItemStatus, MoodEnergy, WardrobeCategory
from app.evidence.rules import EvidenceRuleEngine


def _item(
    *,
    fid: int,
    formality: DresscodeLevel = DresscodeLevel.SMART_CASUAL,
    colors: list[ColorFamily] | None = None,
    tags: list[str] | None = None,
    cat: WardrobeCategory = WardrobeCategory.TOP,
) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=fid,
        name=f"item{fid}",
        category=cat,
        color_families=colors or [ColorFamily.NEUTRAL],
        formality=formality,
        season_tags=[],
        is_available=True,
        status=ItemStatus.CLEAN,
        style_tags=tags or [],
    )


def test_enclothed_cognition_meeting_formal_boost():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.MEETING, mood=MoodEnergy.FOCUS)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, formality=DresscodeLevel.SMART_CASUAL),
        _item(fid=2, cat=WardrobeCategory.BOTTOM, formality=DresscodeLevel.SMART_CASUAL),
        _item(fid=3, cat=WardrobeCategory.SHOES, formality=DresscodeLevel.CASUAL),
    ]
    base = 0.7
    final, adj = eng.apply(base, ctx, items, {"orchestrator_confidence": 0.2})
    assert final >= base
    assert any(a.evidence_id == "enclothed_cognition" for a in adj)


def test_enclothed_cognition_no_boost_for_home():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME, mood=MoodEnergy.FOCUS)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    base = 0.7
    _, adj = eng.apply(base, ctx, items, {"orchestrator_confidence": 0.2})
    assert not any(a.evidence_id == "enclothed_cognition" for a in adj)


def test_choice_overload_minimum_two_tags():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, colors=[ColorFamily.BOLD], tags=["classic"]),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"a": 1, "b": 2, "c": 3, "d": 4})
    ids = {a.evidence_id for a in adj}
    assert "agentic_reco_pipeline" in ids
    assert len(adj) >= 2


def test_capsule_tags_trigger():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, tags=["minimalist"]),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert any(a.evidence_id == "capsule_wardrobe_creativity" for a in adj)


def test_capsule_no_tag_no_capsule_evidence():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, tags=["edgy"]),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert not any(a.evidence_id == "capsule_wardrobe_creativity" for a in adj)


def test_decision_fatigue_trigger_meeting():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.MEETING)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert any(a.evidence_id == "decision_fatigue" for a in adj)


def test_decision_fatigue_not_for_plain_home():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert not any(a.evidence_id == "decision_fatigue" for a in adj)


def test_color_harmony_neutral_boost():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, colors=[ColorFamily.NEUTRAL]),
        _item(fid=2, cat=WardrobeCategory.BOTTOM, colors=[ColorFamily.NEUTRAL]),
        _item(fid=3, cat=WardrobeCategory.SHOES, colors=[ColorFamily.NEUTRAL]),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert any(a.evidence_id == "color_harmony_itten" for a in adj)


def test_cognitive_dissonance_dresscode_override():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(
        event_type=EventType.HOME,
        dresscode_override=DresscodeLevel.SMART_CASUAL,
    )
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP, formality=DresscodeLevel.SMART_CASUAL),
        _item(fid=2, cat=WardrobeCategory.BOTTOM, formality=DresscodeLevel.CASUAL),
        _item(fid=3, cat=WardrobeCategory.SHOES, formality=DresscodeLevel.CASUAL),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert any(a.evidence_id == "cognitive_dissonance" for a in adj)


def test_cognitive_dissonance_missing_when_no_override():
    eng = EvidenceRuleEngine()
    ctx = ContextInput(event_type=EventType.HOME)
    items = [
        _item(fid=1, cat=WardrobeCategory.TOP),
        _item(fid=2, cat=WardrobeCategory.BOTTOM),
        _item(fid=3, cat=WardrobeCategory.SHOES),
    ]
    _, adj = eng.apply(0.5, ctx, items, {"orchestrator_confidence": 0.0})
    assert not any(a.evidence_id == "cognitive_dissonance" for a in adj)
