import asyncio

from app.agents.color_agent import ColorAgent
from app.api.schemas import ContextInput, UserStylePreferences
from app.config import settings
from app.domain.entities import OutfitCandidateDTO, RecommendationPipelineInput, WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType, ItemStatus, MoodEnergy, WardrobeCategory


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


def _item(item_id: int, category: WardrobeCategory, dominant_colors: list[dict]) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=item_id,
        name=f"item-{item_id}",
        category=category,
        color_families=[ColorFamily.NEUTRAL],
        dominant_colors=dominant_colors,
        formality=DresscodeLevel.CASUAL,
        season_tags=[],
        is_available=True,
        status=ItemStatus.CLEAN,
        style_tags=[],
    )


def _pipeline(profile: dict | None = None) -> RecommendationPipelineInput:
    return RecommendationPipelineInput(
        context=ContextInput(event_type=EventType.OTHER, mood=MoodEnergy.FOCUS),
        style_preferences=UserStylePreferences(),
        palette_bias=[],
        items=[],
        color_profile=profile,
    )


def test_color_agent_rewards_complementary_pairs() -> None:
    agent = ColorAgent()
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2],
        items=[
            _item(1, WardrobeCategory.TOP, [{"hex": "#0077CC", "proportion": 0.8, "hue": 205.0, "saturation": 0.7, "lightness": 0.4, "temperature": "cool"}]),
            _item(2, WardrobeCategory.BOTTOM, [{"hex": "#CC5500", "proportion": 0.8, "hue": 25.0, "saturation": 0.8, "lightness": 0.4, "temperature": "warm"}]),
        ],
    )
    result = agent.evaluate(candidate, _pipeline())
    assert result.partial_scores["harmony"] > 0.5


def test_color_agent_penalizes_when_far_from_season_palette() -> None:
    agent = ColorAgent()
    candidate = OutfitCandidateDTO(
        item_ids=[1],
        items=[
            _item(1, WardrobeCategory.TOP, [{"hex": "#FFA500", "proportion": 1.0, "hue": 39.0, "saturation": 1.0, "lightness": 0.5, "temperature": "warm"}]),
        ],
    )
    cool_profile = {"season": "true_winter", "palette": ["#1A1A1A", "#2B2D42", "#4361EE", "#F72585", "#4CC9F0"]}
    result = agent.evaluate(candidate, _pipeline(cool_profile))
    assert result.partial_scores["harmony"] < 0.65
