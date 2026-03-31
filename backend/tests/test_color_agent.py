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
