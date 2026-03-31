from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.agents.color_agent import ColorAgent
from app.bootstrap import get_default_user_id
from app.db.session import get_db
from app.models.profile import UserProfile

router = APIRouter(tags=["profile"])


@router.post("/profile/color-analysis")
async def color_analysis(selfie: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    selfie_bytes = await selfie.read()
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
        "scientific_note": "Color profile uses hue/value/chroma seasonal analysis for wardrobe harmony scoring.",
    }
