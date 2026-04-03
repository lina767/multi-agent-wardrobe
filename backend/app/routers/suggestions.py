from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    CalendarEventRead,
    ContextInput,
    PackingAssistantRequest,
    PackingAssistantResponse,
    ProactiveSuggestionRead,
    ProactiveSuggestionsResponse,
    RecommendationRequest,
    SuggestionFeedbackUpdate,
)
from app.db.models import WardrobeItem
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.domain.enums import ColorFamily
from app.models.profile import OutfitLog, OutfitSuggestion, UserProfile
from app.domain.enums import EventType, MoodEnergy
from app.services.calendar_service import CalendarService
from app.services.recommendation_service import build_recommendations
from app.services.temporal_intelligence import get_current_temporal_state, record_style_signal
from app.services.weather import WeatherService

router = APIRouter(tags=["suggestions"])


def _palette_bias_from_profile(profile: UserProfile | None) -> list[ColorFamily]:
    if not profile or not profile.color_palette:
        return []
    buckets: set[ColorFamily] = set()
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
            buckets.add(ColorFamily.NEUTRAL)
        elif r > b + 20:
            buckets.add(ColorFamily.WARM)
        elif b > r + 20:
            buckets.add(ColorFamily.COOL)
        elif max_c > 170:
            buckets.add(ColorFamily.PASTEL)
        else:
            buckets.add(ColorFamily.EARTH)
    return sorted(buckets, key=lambda c: c.value)


def _occasion_to_event(occasion: str) -> EventType:
    mapping = {
        "casual": EventType.ERRAND,
        "smart casual": EventType.MEETING,
        "event": EventType.OTHER,
        "sport": EventType.ERRAND,
    }
    return mapping.get(occasion.lower(), EventType.OTHER)


def _event_type_from_string(value: str) -> EventType:
    normalized = value.strip().lower()
    for enum_value in EventType:
        if normalized == enum_value.value:
            return enum_value
    return EventType.OTHER


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
            condition=weather_data.get("condition"),
            condition_raw=weather_data.get("condition_raw"),
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
        color_profile={
            "season": profile.color_season if profile else None,
            "undertone": profile.undertone if profile else None,
            "contrast_level": profile.contrast_level if profile else None,
            "palette": profile.color_palette if profile else None,
        },
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
    body: SuggestionFeedbackUpdate,
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
    accepted_value = body.accepted
    if body.thumb == "up":
        accepted_value = True
    elif body.thumb == "down":
        accepted_value = False
    suggestion.accepted = accepted_value if accepted_value is not None else suggestion.accepted
    if body.rating is not None:
        suggestion.mood_score = max(0.0, min(1.0, float(body.rating) / 5.0))
    weight_basis = body.rating if body.rating is not None else (5 if body.thumb == "up" else 2 if body.thumb == "down" else 3)
    record_style_signal(
        db,
        user_id=user_id,
        signal_type="suggestion_feedback",
        source="suggestions_api",
        weight=max(0.2, float(weight_basis) / 5.0),
        payload={
            "suggestion_id": suggestion_id,
            "accepted": accepted_value,
            "rating": body.rating,
            "thumb": body.thumb,
            "reason_tags": body.reason_tags,
            "context": body.context or {},
            "item_ids": suggestion.item_ids,
            "occasion": body.occasion,
        },
    )
    db.commit()
    return {"status": "updated"}


@router.get("/suggestions/proactive", response_model=ProactiveSuggestionsResponse)
async def proactive_suggestions(
    limit: int = Query(default=3, ge=1, le=7),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ProactiveSuggestionsResponse:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    palette_bias = _palette_bias_from_profile(profile)
    events = await CalendarService().list_upcoming_events(limit=limit)
    entries: list[ProactiveSuggestionRead] = []
    for event in events:
        weather_data = await WeatherService().fetch_current(event.location) if event.location else {}
        req = RecommendationRequest(
            context=ContextInput(
                condition=weather_data.get("condition"),
                condition_raw=weather_data.get("condition_raw"),
                temperature_c=weather_data.get("temperature_c"),
                feels_like_c=weather_data.get("feels_like_c"),
                rain_probability=weather_data.get("rain_probability"),
                uv_index=weather_data.get("uv_index"),
                wind_speed_kph=weather_data.get("wind_speed_kph"),
                forecast_summary=weather_data.get("forecast_summary"),
                event_type=_event_type_from_string(event.event_type),
                mood=MoodEnergy.FOCUS,
                notes=f"calendar_event={event.title}",
            ),
            palette_bias=palette_bias,
            max_candidates_to_rank=80,
            color_profile={
                "season": profile.color_season if profile else None,
                "undertone": profile.undertone if profile else None,
                "contrast_level": profile.contrast_level if profile else None,
                "palette": profile.color_palette if profile else None,
            },
        )
        output = build_recommendations(db, user_id, req)
        entries.append(
            ProactiveSuggestionRead(
                event=CalendarEventRead(
                    title=event.title,
                    starts_at=event.starts_at,
                    location=event.location,
                    event_type=event.event_type,
                    source=event.source,
                ),
                suggestions=[
                    {
                        "item_ids": suggestion.item_ids,
                        "item_names": suggestion.item_names,
                        "total_score": suggestion.total_score,
                        "explanation": suggestion.explanation,
                    }
                    for suggestion in output.suggestions[:2]
                ],
            )
        )
    return ProactiveSuggestionsResponse(generated_at=datetime.now(UTC), entries=entries)


@router.post("/suggestions/packing-plan", response_model=PackingAssistantResponse)
async def packing_plan(
    body: PackingAssistantRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> PackingAssistantResponse:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    palette_bias = _palette_bias_from_profile(profile)
    occasions = body.planned_occasions or ["casual"] * body.duration_days
    if len(occasions) < body.duration_days:
        occasions = occasions + [occasions[-1] if occasions else "casual"] * (body.duration_days - len(occasions))
    occasions = occasions[: body.duration_days]
    per_day_outfits: list[dict] = []
    item_frequency: dict[int, int] = {}
    item_names: dict[int, str] = {}
    for day_index, occasion in enumerate(occasions, start=1):
        weather_data = await WeatherService().fetch_current(body.location) if body.location else {}
        req = RecommendationRequest(
            context=ContextInput(
                condition=weather_data.get("condition"),
                condition_raw=weather_data.get("condition_raw"),
                temperature_c=weather_data.get("temperature_c"),
                feels_like_c=weather_data.get("feels_like_c"),
                rain_probability=weather_data.get("rain_probability"),
                uv_index=weather_data.get("uv_index"),
                wind_speed_kph=weather_data.get("wind_speed_kph"),
                forecast_summary=weather_data.get("forecast_summary"),
                event_type=_occasion_to_event(occasion),
                mood=MoodEnergy.FOCUS,
                notes=f"packing_day={day_index}",
            ),
            palette_bias=palette_bias,
            max_candidates_to_rank=100,
        )
        output = build_recommendations(db, user_id, req)
        top = output.suggestions[0] if output.suggestions else None
        if not top:
            continue
        for item_id, item_name in zip(top.item_ids, top.item_names):
            item_frequency[item_id] = item_frequency.get(item_id, 0) + 1
            item_names[item_id] = item_name
        per_day_outfits.append(
            {
                "day": day_index,
                "occasion": occasion,
                "item_ids": top.item_ids,
                "item_names": top.item_names,
                "score": top.total_score,
            }
        )
    ranked_items = sorted(item_frequency, key=lambda item_id: (-item_frequency[item_id], item_id))
    packed_ids = ranked_items[: body.max_items]
    packed_set = set(packed_ids)
    filtered_plan = []
    for outfit in per_day_outfits:
        filtered_ids = [item_id for item_id in outfit["item_ids"] if item_id in packed_set]
        filtered_names = [item_names[item_id] for item_id in filtered_ids if item_id in item_names]
        if not filtered_ids:
            continue
        filtered_plan.append(
            {
                "day": outfit["day"],
                "occasion": outfit["occasion"],
                "item_ids": filtered_ids,
                "item_names": filtered_names,
                "score": outfit["score"],
            }
        )
    coverage = round(len(filtered_plan) / max(1, body.duration_days), 3)
    return PackingAssistantResponse(
        summary={
            "duration_days": body.duration_days,
            "planned_occasions": occasions,
            "coverage_ratio": coverage,
            "selected_item_count": len(packed_ids),
            "laundry_frequency_days": body.laundry_frequency_days,
        },
        packing_item_ids=packed_ids,
        packing_item_names=[item_names[item_id] for item_id in packed_ids if item_id in item_names],
        outfit_plan=filtered_plan,
    )
