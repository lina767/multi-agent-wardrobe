from app.agents.style_agent import StyleAgent
from app.api.schemas import ContextInput, UserStylePreferences
from app.domain.entities import OutfitCandidateDTO, RecommendationPipelineInput, WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType, MoodEnergy, WardrobeCategory


def _item(item_id: int, tags: list[str]) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=item_id,
        name=f"item-{item_id}",
        category=WardrobeCategory.TOP if item_id == 1 else WardrobeCategory.BOTTOM if item_id == 2 else WardrobeCategory.SHOES,
        color_families=[ColorFamily.NEUTRAL],
        formality=DresscodeLevel.CASUAL,
        season_tags=[],
        is_available=True,
        style_tags=tags,
    )


def _pipeline(
    *,
    preferred: list[str] | None = None,
    avoid: list[str] | None = None,
    history_tags: list[str] | None = None,
    history: list[dict] | None = None,
) -> RecommendationPipelineInput:
    return RecommendationPipelineInput(
        context=ContextInput(event_type=EventType.OTHER, mood=MoodEnergy.FOCUS),
        style_preferences=UserStylePreferences(
            preferred_style_tags=preferred or [],
            avoid_style_tags=avoid or [],
        ),
        palette_bias=[],
        items=[],
        outfit_history_tags=history_tags or [],
        outfit_history=history or [],
    )


def test_style_agent_rewards_preferred_and_history_tags() -> None:
    agent = StyleAgent()
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2, 3],
        items=[_item(1, ["minimalist"]), _item(2, ["classic"]), _item(3, ["smart"])],
    )
    result = agent.evaluate(
        candidate,
        _pipeline(preferred=["minimalist", "classic"], history_tags=["classic", "tailored"]),
    )
    assert result.partial_scores["style_fit"] > 0.45
    assert any("explicit style preferences" in r.lower() for r in result.reasons)
    assert any("historically worn" in r.lower() for r in result.reasons)


def test_style_agent_penalizes_avoided_and_negative_feedback() -> None:
    agent = StyleAgent()
    candidate = OutfitCandidateDTO(
        item_ids=[1, 2, 3],
        items=[_item(1, ["streetwear"]), _item(2, ["oversized"]), _item(3, ["sporty"])],
    )
    result = agent.evaluate(
        candidate,
        _pipeline(
            avoid=["streetwear", "oversized"],
            history=[{"item_ids": [1, 2, 3], "rating": 1}],
        ),
    )
    assert result.partial_scores["style_fit"] < 0.45
    assert any("avoided" in r.lower() for r in result.reasons)
    assert any("negative feedback" in r.lower() for r in result.reasons)


def test_weighted_style_counts_boosts_high_rated_worn_tags() -> None:
    agent = StyleAgent()
    counts = agent._weighted_style_counts_from_context(
        outfit_history=[
            {"style_tags": ["minimalist"], "rating": 5},
            {"style_tags": ["minimalist"], "rating": 2},
            {"style_tags": ["edgy"], "rating": 4},
        ],
        wardrobe_items=[{"style_tags": ["minimalist"]}, {"style_tags": ["edgy"]}],
    )
    assert counts["minimalist"] > counts["edgy"]
