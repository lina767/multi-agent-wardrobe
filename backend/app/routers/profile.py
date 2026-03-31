from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import (
    ColorProfileFeedbackCreate,
    ColorProfileFeedbackRead,
    OnboardingRequest,
    OnboardingResponse,
    ProfileRead,
    ProfileCheckinCreate,
    ProfileCheckinRead,
    ProfileUpdate,
    TemporalStateRead,
)
from app.agents.color_agent import ColorAgent
from app.api.schemas import ContextInput, RecommendationRequest
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.profile import ColorFeedbackEvent, UserCheckin, UserProfile
from app.domain.enums import EventType, MoodEnergy
from app.services.recommendation_service import build_recommendations
from app.services.temporal_intelligence import create_checkin, get_current_temporal_state, record_style_signal
from app.services.weather import WeatherService

router = APIRouter(tags=["profile"])
PROFILE_MEDIA_DIR = Path(__file__).resolve().parents[2] / "data" / "profile"
PROFILE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def _profile_media_url(filename: str) -> str:
    return f"/media/profile/{filename}"


def _build_profile_response(user: User, profile: UserProfile | None) -> ProfileRead:
    preferences = user.preferences_json or {}
    return ProfileRead(
        name=user.display_name,
        age=preferences.get("age"),
        life_phase=preferences.get("life_phase"),
        cold_sensitivity=preferences.get("cold_sensitivity"),
        selfie_url=preferences.get("selfie_url"),
        figure_analysis=preferences.get("figure_analysis"),
        color_profile=(
            {
                "season": profile.color_season,
                "undertone": profile.undertone,
                "contrast_level": profile.contrast_level,
                "palette": profile.color_palette,
            }
            if profile
            else None
        ),
    )


@router.post("/profile/color-analysis")
async def color_analysis(
    photo: UploadFile | None = File(None),
    selfie: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    # Backward-compatible: accept legacy "selfie" field and prefer "photo".
    image = photo or selfie
    if image is None:
        raise HTTPException(status_code=400, detail="Missing photo upload")
    selfie_bytes = await image.read()
    agent = ColorAgent()
    color_profile = await agent.analyze_selfie(selfie_bytes)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    profile.color_season = color_profile["season"]
    profile.undertone = color_profile["undertone"]
    profile.contrast_level = color_profile["contrast_level"]
    profile.color_palette = color_profile["palette"]
    profile.selfie_analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return {
        "season": profile.color_season,
        "undertone": profile.undertone,
        "contrast_level": profile.contrast_level,
        "palette": profile.color_palette,
        "confidence": color_profile.get("confidence"),
        "backend": color_profile.get("backend"),
        "used_fallback": bool(color_profile.get("used_fallback")),
        "scientific_note": "Color profile uses face and visible body contrast cues with hue/value/chroma seasonal analysis for wardrobe harmony scoring.",
    }


@router.get("/profile/me", response_model=ProfileRead)
def get_profile_me(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ProfileRead:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return _build_profile_response(user, profile)


@router.patch("/profile/me", response_model=ProfileRead)
def update_profile_me(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ProfileRead:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    preferences = dict(user.preferences_json or {})
    payload = body.model_dump(exclude_unset=True)
    if "name" in payload:
        user.display_name = payload["name"]
    for key in ("age", "life_phase", "cold_sensitivity", "figure_analysis"):
        if key in payload:
            preferences[key] = payload[key]
    user.preferences_json = preferences
    db.commit()
    db.refresh(user)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return _build_profile_response(user, profile)


@router.post("/profile/selfie", response_model=ProfileRead)
async def upload_profile_selfie(
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ProfileRead:
    if not selfie.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = selfie.filename.split(".")[-1].lower() if "." in selfie.filename else ""
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    payload = await selfie.read()
    filename = f"user_{user_id}_{int(datetime.now(UTC).timestamp())}.{ext}"
    path = PROFILE_MEDIA_DIR / filename
    path.write_bytes(payload)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    preferences = dict(user.preferences_json or {})
    preferences["selfie_url"] = _profile_media_url(filename)
    user.preferences_json = preferences
    db.commit()
    db.refresh(user)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return _build_profile_response(user, profile)


@router.post("/profile/checkins", response_model=ProfileCheckinRead)
def add_checkin(
    body: ProfileCheckinCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ProfileCheckinRead:
    row = create_checkin(db, user_id=user_id, body=body)
    return ProfileCheckinRead.model_validate(row)


@router.get("/profile/checkins", response_model=list[ProfileCheckinRead])
def list_checkins(
    limit: int = 30,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> list[ProfileCheckinRead]:
    rows = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user_id)
        .order_by(UserCheckin.effective_from.desc())
        .limit(max(1, min(200, limit)))
        .all()
    )
    return [ProfileCheckinRead.model_validate(row) for row in rows]


@router.get("/profile/state", response_model=TemporalStateRead)
def get_profile_state(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> TemporalStateRead:
    state = get_current_temporal_state(db, user_id=user_id)
    updated_at = state.get("updated_at")
    if not isinstance(updated_at, datetime):
        updated_at = datetime.now(UTC)
    return TemporalStateRead(
        user_id=user_id,
        state_key="current",
        features={k: v for k, v in state.items() if k not in {"dynamic_weights", "state_factors", "confidence", "updated_at"}},
        dynamic_weights=dict(state.get("dynamic_weights", {})),
        state_factors=list(state.get("state_factors", [])),
        confidence=float(state.get("confidence", 0.5)),
        updated_at=updated_at,
    )


@router.post("/profile/color-feedback", response_model=ColorProfileFeedbackRead)
def submit_color_feedback(
    body: ColorProfileFeedbackCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ColorProfileFeedbackRead:
    row = ColorFeedbackEvent(
        user_id=user_id,
        source=body.source,
        predicted_season=body.predicted_season,
        predicted_undertone=body.predicted_undertone,
        predicted_contrast_level=body.predicted_contrast_level,
        predicted_confidence=body.predicted_confidence,
        corrected_season=body.corrected_season,
        corrected_undertone=body.corrected_undertone,
        corrected_contrast_level=body.corrected_contrast_level,
        note=body.note,
    )
    db.add(row)
    record_style_signal(
        db,
        user_id=user_id,
        signal_type="color_profile_feedback",
        source="profile_api",
        weight=0.9 if body.corrected_season else 0.6,
        payload={
            "predicted_season": body.predicted_season,
            "predicted_undertone": body.predicted_undertone,
            "predicted_contrast_level": body.predicted_contrast_level,
            "predicted_confidence": body.predicted_confidence,
            "corrected_season": body.corrected_season,
            "corrected_undertone": body.corrected_undertone,
            "corrected_contrast_level": body.corrected_contrast_level,
        },
    )
    db.commit()
    db.refresh(row)
    return ColorProfileFeedbackRead.model_validate(row)


@router.post("/profile/onboarding", response_model=OnboardingResponse)
async def run_onboarding(
    body: OnboardingRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> OnboardingResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    preferences = dict(user.preferences_json or {})
    if body.name:
        user.display_name = body.name
    preferences["age"] = body.age
    preferences["life_phase"] = body.life_phase
    preferences["cold_sensitivity"] = body.cold_sensitivity
    preferences["figure_analysis"] = body.figure_analysis
    user.preferences_json = preferences

    checkin = create_checkin(
        db,
        user_id=user_id,
        body=ProfileCheckinCreate(
            life_phase=body.life_phase,
            style_goals=["onboarding_setup"],
            fit_confidence=0.6,
        ),
    )
    db.refresh(checkin)

    weather_data: dict = {}
    if body.location:
        weather_data = await WeatherService().fetch_current(body.location)
    profile_model = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
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
            event_type=EventType.OTHER,
            mood=MoodEnergy.FOCUS,
            notes="onboarding_bootstrap",
        ),
        color_profile={
            "season": profile_model.color_season if profile_model else None,
            "undertone": profile_model.undertone if profile_model else None,
            "contrast_level": profile_model.contrast_level if profile_model else None,
            "palette": profile_model.color_palette if profile_model else None,
        },
        max_candidates_to_rank=60,
    )
    recommendations = build_recommendations(db, user_id, req)
    state = get_current_temporal_state(db, user_id=user_id)
    db.commit()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    updated_user = db.query(User).filter(User.id == user_id).first()
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_at = state.get("updated_at")
    if not isinstance(updated_at, datetime):
        updated_at = datetime.now(UTC)
    return OnboardingResponse(
        profile=_build_profile_response(updated_user, profile),
        temporal_state=TemporalStateRead(
            user_id=user_id,
            state_key="current",
            features={k: v for k, v in state.items() if k not in {"dynamic_weights", "state_factors", "confidence", "updated_at"}},
            dynamic_weights=dict(state.get("dynamic_weights", {})),
            state_factors=list(state.get("state_factors", [])),
            confidence=float(state.get("confidence", 0.5)),
            updated_at=updated_at,
        ),
        suggestions=[
            {
                "item_names": suggestion.item_names,
                "total_score": suggestion.total_score,
                "explanation": suggestion.explanation,
            }
            for suggestion in recommendations.suggestions[:3]
        ],
    )
