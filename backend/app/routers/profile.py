from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import (
    ColorProfileFeedbackCreate,
    ColorProfileFeedbackRead,
    ProfileCheckinCreate,
    ProfileCheckinRead,
    TemporalStateRead,
)
from app.agents.color_agent import ColorAgent
from app.bootstrap import get_default_user_id
from app.db.session import get_db
from app.models.profile import ColorFeedbackEvent, UserCheckin, UserProfile
from app.services.temporal_intelligence import create_checkin, get_current_temporal_state, record_style_signal

router = APIRouter(tags=["profile"])


@router.post("/profile/color-analysis")
async def color_analysis(
    photo: UploadFile | None = File(None),
    selfie: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> dict:
    # Backward-compatible: accept legacy "selfie" field and prefer "photo".
    image = photo or selfie
    if image is None:
        raise HTTPException(status_code=400, detail="Missing photo upload")
    selfie_bytes = await image.read()
    agent = ColorAgent()
    color_profile = await agent.analyze_selfie(selfie_bytes)
    user_id = get_default_user_id(db)
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


@router.post("/profile/checkins", response_model=ProfileCheckinRead)
def add_checkin(body: ProfileCheckinCreate, db: Session = Depends(get_db)) -> ProfileCheckinRead:
    user_id = get_default_user_id(db)
    row = create_checkin(db, user_id=user_id, body=body)
    return ProfileCheckinRead.model_validate(row)


@router.get("/profile/checkins", response_model=list[ProfileCheckinRead])
def list_checkins(limit: int = 30, db: Session = Depends(get_db)) -> list[ProfileCheckinRead]:
    user_id = get_default_user_id(db)
    rows = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user_id)
        .order_by(UserCheckin.effective_from.desc())
        .limit(max(1, min(200, limit)))
        .all()
    )
    return [ProfileCheckinRead.model_validate(row) for row in rows]


@router.get("/profile/state", response_model=TemporalStateRead)
def get_profile_state(db: Session = Depends(get_db)) -> TemporalStateRead:
    user_id = get_default_user_id(db)
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
def submit_color_feedback(body: ColorProfileFeedbackCreate, db: Session = Depends(get_db)) -> ColorProfileFeedbackRead:
    user_id = get_default_user_id(db)
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
