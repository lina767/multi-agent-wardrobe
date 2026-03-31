from app.api.schemas import ContextInput, RecommendationRequest, UserStylePreferences
from app.domain.entities import OutfitCandidateDTO, WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, EventType, ItemStatus, MoodEnergy, WardrobeCategory
from app.services.recommendation_service import (
    _build_retrieval_query,
    _prioritize_candidates_by_vector_hits,
)


def _item(item_id: int, category: WardrobeCategory) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=item_id,
        name=f"item-{item_id}",
        category=category,
        color_families=[ColorFamily.NEUTRAL],
        dominant_colors=[],
        formality=DresscodeLevel.CASUAL,
        season_tags=[],
        is_available=True,
        status=ItemStatus.CLEAN,
        style_tags=[],
    )


def test_prioritizes_candidates_with_more_hit_overlap() -> None:
    c1 = OutfitCandidateDTO(item_ids=[1, 2, 3], items=[_item(1, WardrobeCategory.TOP)])
    c2 = OutfitCandidateDTO(item_ids=[4, 5, 6], items=[_item(4, WardrobeCategory.TOP)])
    c3 = OutfitCandidateDTO(item_ids=[1, 5, 9], items=[_item(1, WardrobeCategory.TOP)])
    out = _prioritize_candidates_by_vector_hits([c1, c2, c3], [1, 5, 8])
    assert out[0].item_ids == [1, 5, 9]
    assert out[1].item_ids == [1, 2, 3]
    assert out[2].item_ids == [4, 5, 6]


def test_build_retrieval_query_includes_context_and_style_signals() -> None:
    req = RecommendationRequest(
        context=ContextInput(
            event_type=EventType.MEETING,
            mood=MoodEnergy.FOCUS,
            forecast_summary="Light rain expected",
            notes="Need polished outfit",
        ),
        style_preferences=UserStylePreferences(
            preferred_style_tags=["minimalist", "business-casual"],
            avoid_style_tags=["streetwear"],
        ),
        palette_bias=[ColorFamily.NEUTRAL, ColorFamily.COOL],
    )
    query = _build_retrieval_query(req, req.style_preferences)
    assert "event:meeting" in query
    assert "mood:focus" in query
    assert "minimalist" in query
    assert "avoid:streetwear" in query
