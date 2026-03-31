from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.wardrobe_agent import WardrobeAgent
from app.bootstrap import get_default_user_id
from app.db.models import WardrobeItem
from app.models.profile import UserProfile
from app.db.session import get_db

router = APIRouter(tags=["analytics"])


@router.get("/wardrobe/analytics")
def wardrobe_analytics(db: Session = Depends(get_db)) -> dict:
    user_id = get_default_user_id(db)
    rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "color_families": list(r.color_families_json or []),
            "style_tags": list(r.style_tags_json or []),
            "season_tags": list(r.season_tags_json or []),
            "is_available": r.is_available,
        }
        for r in rows
    ]
    color_profile = {"palette": profile.color_palette} if profile and profile.color_palette else None
    return WardrobeAgent().analyze_wardrobe(items, color_profile=color_profile)
