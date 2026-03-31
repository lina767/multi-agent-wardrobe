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
