from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import ContextInput, RecommendationRequest
from app.db.models import WardrobeItem
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.profile import OutfitLog, OutfitSuggestion, UserProfile
from app.domain.enums import EventType, MoodEnergy
from app.services.recommendation_service import build_recommendations
from app.services.temporal_intelligence import get_current_temporal_state, record_style_signal
from app.services.weather import WeatherService

router = APIRouter(tags=["suggestions"])


def _palette_bias_from_profile(profile: UserProfile | None) -> list[str]:
    if not profile or not profile.color_palette:
        return []
    buckets: set[str] = set()
    for value in profile.color_palette:
        if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
            continue
        try:
            r = int(value[1:3], 16)
            g = int(value[3:5], 16)
            b = int(value[5:7], 16)
        except ValueError:
            continue
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        if max_c - min_c < 20:
            buckets.add("neutral")
        elif r > b + 20:
            buckets.add("warm")
        elif b > r + 20:
            buckets.add("cool")
        elif max_c > 170:
            buckets.add("pastel")
        else:
            buckets.add("earth")
    return sorted(buckets)


def _occasion_to_event(occasion: str) -> EventType:
    mapping = {
        "work": EventType.MEETING,
        "date": EventType.DATE,
        "casual": EventType.ERRAND,
        "active": EventType.ERRAND,
        "event": EventType.OTHER,
    }
    return mapping.get(occasion.lower(), EventType.OTHER)


@router.get("/suggestions")
async def get_suggestions(
    mood: str = Query(default="focus"),
    occasion: str = Query(default="casual"),
    location: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
    if not rows:
        raise HTTPException(status_code=400, detail="No wardrobe items found. Add items first.")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    palette_bias = _palette_bias_from_profile(profile)

    mood_value = mood.lower()
    try:
        mood_enum = MoodEnergy(mood_value)
    except ValueError:
        mood_enum = MoodEnergy.FOCUS

    weather_data = {}
    if location:
        weather_data = await WeatherService().fetch_current(location)

    req = RecommendationRequest(
        context=ContextInput(
            temperature_c=weather_data.get("temperature_c"),
            feels_like_c=weather_data.get("feels_like_c"),
            rain_probability=weather_data.get("rain_probability"),
            uv_index=weather_data.get("uv_index"),
            wind_speed_kph=weather_data.get("wind_speed_kph"),
            forecast_summary=weather_data.get("forecast_summary"),
            event_type=_occasion_to_event(occasion),
            mood=mood_enum,
            notes=f"occasion={occasion.lower()} location={location or ''}".strip(),
        ),
        palette_bias=palette_bias,
        max_candidates_to_rank=120,
    )
    output = build_recommendations(db, user_id, req)
    temporal_state = get_current_temporal_state(db, user_id=user_id)
    saved = []
    for suggestion in output.suggestions:
        partials: dict[str, float] = {}
        for contrib in suggestion.agent_contributions:
            partials.update(contrib.partial_scores)
        breakdown = {
            "color_score": round(partials.get("harmony", 0.0), 3),
            "style_score": round(partials.get("style_fit", 0.0), 3),
            "context_score": round(partials.get("context_fit", 0.0), 3),
            "mood_alignment": round(partials.get("style_fit", 0.0), 3),
            "sustainability": round(partials.get("wardrobe_coherence", 0.0), 3),
        }
        model = OutfitSuggestion(
            user_id=user_id,
            item_ids=suggestion.item_ids,
            color_score=breakdown["color_score"],
            style_score=breakdown["style_score"],
            context_score=breakdown["context_score"],
            mood_score=breakdown["mood_alignment"],
            total_score=suggestion.total_score,
            reasoning=suggestion.explanation,
        )
        db.add(model)
        db.flush()
        saved.append(
            {
                "id": model.id,
                "items": suggestion.item_ids,
                "item_names": suggestion.item_names,
                "total_score": suggestion.total_score,
                "reasoning_breakdown": breakdown,
                "explanation": suggestion.explanation,
                "evidence_tags": [e.model_dump() for e in suggestion.evidence_tags],
            }
        )
    db.commit()
    return {
        "context": {
            "mood": mood_enum.value,
            "occasion": occasion.lower(),
            "weather": weather_data,
        },
        "style_profile": {
            "temporal_state": {
                "life_phase": temporal_state.get("life_phase"),
                "dominant_occasion": temporal_state.get("dominant_occasion"),
                "fit_confidence": temporal_state.get("fit_confidence"),
                "state_factors": temporal_state.get("state_factors", []),
            },
            "dynamic_weights": temporal_state.get("dynamic_weights", {}),
        },
        "color_profile": {
            "season": profile.color_season if profile else None,
            "undertone": profile.undertone if profile else None,
            "contrast_level": profile.contrast_level if profile else None,
            "palette": profile.color_palette if profile else None,
        },
        "wardrobe": {
            "outfit_potential": len(output.suggestions),
            "capsule_suggestions": [],
        },
        "suggestions": saved[:3],
        "scientific_note": "We reduce choice overload by returning only 3 ranked outfits.",
    }


@router.post("/outfits/log")
def log_outfit(
    body: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    item_ids = body.get("item_ids", [])
    model = OutfitLog(
        user_id=user_id,
        item_ids_json=json.dumps(item_ids),
        context_json=body,
    )
    db.add(model)
    record_style_signal(
        db,
        user_id=user_id,
        signal_type="outfit_worn",
        source="outfit_log",
        weight=0.85,
        payload={
            "item_ids": item_ids,
            "occasion": body.get("occasion"),
            "mood": body.get("mood"),
            "style_goals": body.get("style_goals", []),
        },
    )
    db.commit()
    db.refresh(model)
    return {"id": model.id, "status": "logged"}


@router.post("/suggestions/{suggestion_id}/feedback")
def suggestion_feedback(
    suggestion_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    suggestion = (
        db.query(OutfitSuggestion)
        .filter(OutfitSuggestion.id == suggestion_id, OutfitSuggestion.user_id == user_id)
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    suggestion.accepted = bool(body.get("accepted")) if body.get("accepted") is not None else suggestion.accepted
    if body.get("rating") is not None:
        suggestion.mood_score = max(0.0, min(1.0, float(body["rating"]) / 5.0))
    record_style_signal(
        db,
        user_id=user_id,
        signal_type="suggestion_feedback",
        source="suggestions_api",
        weight=max(0.2, float(body.get("rating", 3)) / 5.0),
        payload={
            "suggestion_id": suggestion_id,
            "accepted": body.get("accepted"),
            "rating": body.get("rating"),
            "item_ids": suggestion.item_ids,
            "occasion": body.get("occasion"),
        },
    )
    db.commit()
    return {"status": "updated"}
