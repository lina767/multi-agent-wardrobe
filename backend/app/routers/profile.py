from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.bootstrap import get_default_user_id
from app.db.session import get_db
from app.models.profile import UserProfile

router = APIRouter(tags=["profile"])


@router.post("/profile/color-analysis")
async def color_analysis(selfie: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    _ = await selfie.read()
    user_id = get_default_user_id(db)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    # Phase 1 deterministic placeholder; Claude Vision lands in Phase 2.
    profile.color_season = "true_summer"
    profile.undertone = "cool"
    profile.contrast_level = "medium"
    profile.color_palette = ["#8FA8C9", "#C9D7E8", "#7A8C6E", "#B5727A", "#F8F6F1"]
    profile.selfie_analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return {
        "season": profile.color_season,
        "undertone": profile.undertone,
        "contrast_level": profile.contrast_level,
        "palette": profile.color_palette,
    }
