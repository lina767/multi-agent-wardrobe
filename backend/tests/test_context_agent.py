from app.agents.context_agent import ContextAgent
from app.api.schemas import ContextInput, UserStylePreferences
from app.domain.entities import OutfitCandidateDTO, RecommendationPipelineInput, WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType, ItemStatus, MoodEnergy, WardrobeCategory


def _item(
    item_id: int,
    name: str,
    category: WardrobeCategory,
    material: str | None = None,
    style_tags: list[str] | None = None,
) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=item_id,
        name=name,
        category=category,
        color_families=[ColorFamily.NEUTRAL],
        dominant_colors=[],
        formality=DresscodeLevel.CASUAL,
        season_tags=[],
        is_available=True,
        status=ItemStatus.CLEAN,
        style_tags=style_tags or [],
        material=material,
    )


def _pipeline(context: ContextInput, items: list[WardrobeItemDTO]) -> RecommendationPipelineInput:
    return RecommendationPipelineInput(
        context=context,
        style_preferences=UserStylePreferences(),
        palette_bias=[],
        items=items,
    )


def test_rain_penalizes_without_water_resistance() -> None:
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2, 3],
        items=[
            _item(1, "Cotton tee", WardrobeCategory.TOP, material="cotton"),
            _item(2, "Denim pants", WardrobeCategory.BOTTOM, material="denim"),
            _item(3, "Sneakers", WardrobeCategory.SHOES, material="canvas"),
        ],
    )
    ctx = ContextInput(event_type=EventType.OTHER, mood=MoodEnergy.FOCUS, rain_probability=0.9)
    result = ContextAgent().evaluate(candidate, _pipeline(ctx, candidate.items))
    assert result.partial_scores["context_fit"] < 0.82
    assert any("rain" in reason.lower() for reason in result.reasons)


def test_high_uv_rewards_hat_accessory() -> None:
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2, 3, 4],
        items=[
            _item(1, "Linen shirt", WardrobeCategory.TOP),
            _item(2, "Chinos", WardrobeCategory.BOTTOM),
            _item(3, "Loafers", WardrobeCategory.SHOES),
            _item(4, "Sun hat", WardrobeCategory.ACCESSORY, style_tags=["outdoor"]),
        ],
    )
    ctx = ContextInput(event_type=EventType.OTHER, mood=MoodEnergy.FOCUS, uv_index=8)
    result = ContextAgent().evaluate(candidate, _pipeline(ctx, candidate.items))
    assert result.partial_scores["context_fit"] > 0.82
    assert any("uv" in reason.lower() for reason in result.reasons)


def test_strong_wind_penalizes_flowy_silhouette() -> None:
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2, 3],
        items=[
            _item(1, "Flowy blouse", WardrobeCategory.TOP, style_tags=["flowy"]),
            _item(2, "Wide skirt", WardrobeCategory.BOTTOM, style_tags=["flowy"]),
            _item(3, "Boots", WardrobeCategory.SHOES),
        ],
    )
    ctx = ContextInput(event_type=EventType.OTHER, mood=MoodEnergy.FOCUS, wind_speed_kph=42)
    result = ContextAgent().evaluate(candidate, _pipeline(ctx, candidate.items))
    assert result.partial_scores["context_fit"] < 0.82
    assert any("wind" in reason.lower() for reason in result.reasons)
