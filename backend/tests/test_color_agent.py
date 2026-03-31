import asyncio

from app.agents.color_agent import ColorAgent
from app.config import settings


def test_color_agent_low_confidence_uses_fallback(monkeypatch) -> None:
    agent = ColorAgent()

    def _mock_backend(_self, _bytes: bytes) -> dict:
        return {
            "season": "bright_winter",
            "undertone": "cool",
            "contrast_level": "high",
            "palette": ["#FFFFFF", "#111111", "#2244FF", "#EE3366", "#88AAFF"],
            "confidence": 0.2,
        }

    monkeypatch.setattr(ColorAgent, "_call_claude_vision", _mock_backend)
    monkeypatch.setattr(settings, "color_agent_backend", "anthropic_vision")
    monkeypatch.setattr(settings, "color_profile_min_confidence", 0.65)
    output = asyncio.run(agent.analyze_selfie(b"fake-bytes"))
    assert output["used_fallback"] is True
    assert output["fallback_reason"] == "low_confidence"
    assert output["backend"] == "heuristic"


def test_color_agent_shadow_mode_attaches_shadow(monkeypatch) -> None:
    monkeypatch.setattr(settings, "color_agent_shadow_mode", True)
    monkeypatch.setattr(settings, "color_agent_backend", "heuristic")
    monkeypatch.setattr(settings, "color_profile_min_confidence", 0.1)
    agent = ColorAgent()
    output = asyncio.run(agent.analyze_selfie(b"fake-bytes"))
    assert "shadow" in output
    assert "backend" in output["shadow"]


def test_color_agent_resolve_backend_fallback() -> None:
    assert ColorAgent._resolve_backend("fine_tuned") == "fine_tuned"
    assert ColorAgent._resolve_backend("invalid-backend") == "anthropic_vision"


def test_color_agent_normalize_profile_sanitizes_fields() -> None:
    agent = ColorAgent()
    normalized = agent._normalize_profile(
        {
            "season": "not-a-season",
            "undertone": None,
            "contrast_level": None,
            "palette": ["#aabbcc", "bad", 123],
            "confidence": 9.0,
        },
        "heuristic",
    )
    assert normalized["season"] == "true_summer"
    assert normalized["palette"][0] == "#AABBCC"
    assert normalized["confidence"] == 1.0
    assert normalized["backend"] == "heuristic"


def test_color_agent_fine_tuned_without_endpoint_uses_heuristic(monkeypatch) -> None:
    monkeypatch.setattr(settings, "color_agent_backend", "fine_tuned")
    monkeypatch.setattr(settings, "color_fine_tuned_endpoint", "")
    monkeypatch.setattr(settings, "color_profile_min_confidence", 0.1)
    agent = ColorAgent()
    out = asyncio.run(agent.analyze_selfie(b"fake-bytes"))
    assert out["backend"] == "fine_tuned"
    assert out["season"] in {"true_summer", "soft_autumn"}


def test_color_agent_shadow_failure_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(settings, "color_agent_shadow_mode", True)
    monkeypatch.setattr(settings, "color_agent_backend", "heuristic")
    monkeypatch.setattr(settings, "color_profile_min_confidence", 0.1)

    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ColorAgent, "_call_claude_vision", _raise)
    agent = ColorAgent()
    out = asyncio.run(agent.analyze_selfie(b"fake-bytes"))
    assert out["shadow"]["status"] == "failed"
