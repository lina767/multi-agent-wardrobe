import asyncio

from app.agents.orchestrator import OrchestratorAgent
from app.domain.entities import AgentEvaluationResult
from app.domain.enums import EventType


def _r(name: str, **scores: float) -> AgentEvaluationResult:
    return AgentEvaluationResult(agent_name=name, partial_scores=dict(scores), reasons=[], trace=[])


def test_meeting_upweights_context():
    orch = OrchestratorAgent()
    results = [
        _r("color", harmony=0.9),
        _r("style", style_fit=0.5),
        _r("wardrobe", wardrobe_coherence=0.8),
        _r("context", context_fit=0.95),
    ]
    total, partials, reasons, trace, conf = orch.merge(results, EventType.MEETING)
    assert "context_fit" in partials
    assert total > 0
    assert conf >= 0
    assert any("meeting" in r.lower() for r in reasons)


def test_home_weights_differ_from_meeting():
    orch = OrchestratorAgent()
    results = [
        _r("color", harmony=0.7),
        _r("style", style_fit=0.7),
        _r("wardrobe", wardrobe_coherence=0.7),
        _r("context", context_fit=0.7),
    ]
    t_meeting, _, _, _, _ = orch.merge(results, EventType.MEETING)
    t_home, _, _, _, _ = orch.merge(results, EventType.HOME)
    assert isinstance(t_meeting, float)
    assert isinstance(t_home, float)


def test_merge_applies_weight_overrides():
    orch = OrchestratorAgent()
    results = [
        _r("color", harmony=0.1),
        _r("style", style_fit=0.1),
        _r("wardrobe", wardrobe_coherence=0.1),
        _r("context", context_fit=1.0),
    ]
    baseline, _, _, _, _ = orch.merge(results, EventType.HOME)
    boosted, _, _, _, _ = orch.merge(
        results,
        EventType.HOME,
        weight_overrides={"harmony": 0.05, "style_fit": 0.05, "wardrobe_coherence": 0.1, "context_fit": 0.8},
    )
    assert boosted > baseline


def test_merge_normalizes_invalid_weight_overrides():
    orch = OrchestratorAgent()
    results = [_r("color", harmony=1.0)]
    total, _, _, _, _ = orch.merge(
        results,
        EventType.HOME,
        weight_overrides={"harmony": 4.0, "style_fit": -2.0, "context_fit": 0.0},
    )
    assert 0.0 <= total <= 1.0


def test_supervise_falls_back_without_api_key():
    orch = OrchestratorAgent()
    out = asyncio.run(
        orch.supervise(
            event_type=EventType.HOME,
            context={"event_type": "home", "temperature_c": 20, "mood": "focus"},
            candidates=[
                {
                    "candidate_key": "1-2-3",
                    "total_pre_evidence": 0.72,
                    "fallback_reason": "Deterministic baseline.",
                },
                {
                    "candidate_key": "4-5-6",
                    "total_pre_evidence": 0.61,
                    "fallback_reason": "Deterministic baseline.",
                },
            ],
        )
    )
    assert out["final_ranking"] == ["1-2-3", "4-5-6"]
    assert "adjusted_weights" in out
    assert "harmony" in out["adjusted_weights"]


def test_validate_supervisor_payload_normalizes_and_filters():
    orch = OrchestratorAgent()
    fallback = {
        "adjusted_weights": {"harmony": 0.25, "style_fit": 0.25, "wardrobe_coherence": 0.2, "context_fit": 0.3},
        "final_ranking": ["1-2-3", "4-5-6"],
        "synthesis_text": {"1-2-3": "fallback one", "4-5-6": "fallback two"},
        "conflict_flags": {"1-2-3": [], "4-5-6": []},
    }
    payload = {
        "adjusted_weights": {"harmony": 3, "style_fit": 1, "wardrobe_coherence": 0, "context_fit": 0},
        "final_ranking": ["4-5-6", "oops", "4-5-6"],
        "synthesis_text": {"4-5-6": "haiku text"},
        "conflict_flags": {
            "4-5-6": ["weather_mismatch", "invalid_flag", "weather_mismatch"],
            "1-2-3": ["mood_conflict"],
        },
    }
    out = orch._validate_supervisor_payload(
        payload=payload,
        fallback=fallback,
        default_weights=fallback["adjusted_weights"],
        candidate_keys=["1-2-3", "4-5-6"],
    )
    assert out["final_ranking"] == ["4-5-6", "1-2-3"]
    assert out["conflict_flags"]["4-5-6"] == ["weather_mismatch"]
    assert out["conflict_flags"]["1-2-3"] == ["mood_conflict"]
    assert out["synthesis_text"]["1-2-3"] == "fallback one"
    assert abs(sum(out["adjusted_weights"].values()) - 1.0) < 0.001
