from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.color_agent import ColorAgent
from app.agents.context_agent import ContextAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.style_agent import StyleAgent
from app.agents.wardrobe_agent import WardrobeAgent
from app.bootstrap import get_default_user_id
from app.db.models import WardrobeItem
from app.db.session import get_db
from app.models.profile import OutfitLog, OutfitSuggestion, UserProfile

router = APIRouter(tags=["suggestions"])


def _to_item_dict(row: WardrobeItem) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "color_families": list(row.color_families_json or []),
        "style_tags": list(row.style_tags_json or []),
        "season_tags": list(row.season_tags_json or []),
        "is_available": row.is_available,
        "material": row.material,
        "image_path": row.image_path,
        "formality_score": 0.7 if row.formality in {"business", "formal"} else 0.5 if row.formality == "smart_casual" else 0.3,
    }


@router.get("/suggestions")
async def get_suggestions(
    mood: str = Query(default="focus"),
    occasion: str = Query(default="casual"),
    location: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    user_id = get_default_user_id(db)
    rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
    if not rows:
        raise HTTPException(status_code=400, detail="No wardrobe items found. Add items first.")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    context = AgentContext(
        user_id=user_id,
        wardrobe_items=[_to_item_dict(r) for r in rows],
        mood=mood.lower(),
        occasion=occasion.lower(),
        location=location,
        shared={},
    )
    wardrobe_output = await WardrobeAgent().run(context)
    context_output = await ContextAgent().run(context)
    context.weather = context_output.payload.get("weather", {})
    context.shared["context_filters"] = context_output.payload
    if profile and profile.color_palette:
        context.shared["color_profile"] = {
            "season": profile.color_season,
            "undertone": profile.undertone,
            "contrast_level": profile.contrast_level,
            "palette": profile.color_palette,
        }
    color_output = await ColorAgent().run(context)
    style_output = await StyleAgent().run(context)
    context.shared["item_color_scores"] = color_output.payload.get("item_color_scores", {})
    context.shared["mood_formulas"] = style_output.payload.get("mood_formulas", {})
    orchestrated = await OrchestratorAgent().run(context)
    saved = []
    for suggestion in orchestrated.payload["suggestions"]:
        breakdown = suggestion["reasoning_breakdown"]
        model = OutfitSuggestion(
            user_id=user_id,
            item_ids=suggestion["items"],
            color_score=breakdown["color_score"],
            style_score=breakdown["style_score"],
            context_score=breakdown["context_score"],
            mood_score=breakdown["mood_alignment"],
            total_score=suggestion["total_score"],
            reasoning=suggestion["explanation"],
        )
        db.add(model)
        db.flush()
        saved.append({"id": model.id, **suggestion})
    db.commit()
    return {
        "context": context_output.payload,
        "style_profile": style_output.payload.get("style_profile", {}),
        "color_profile": color_output.payload.get("color_profile", {}),
        "wardrobe": {
            "outfit_potential": wardrobe_output.payload["outfit_potential"],
            "capsule_suggestions": wardrobe_output.payload["capsule_suggestions"],
        },
        "suggestions": saved[:3],
        "scientific_note": "We reduce choice overload by returning only 3 ranked outfits.",
    }


@router.post("/outfits/log")
def log_outfit(body: dict, db: Session = Depends(get_db)) -> dict:
    user_id = get_default_user_id(db)
    item_ids = body.get("item_ids", [])
    model = OutfitLog(
        user_id=user_id,
        item_ids_json=json.dumps(item_ids),
        context_json=body,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return {"id": model.id, "status": "logged"}


@router.post("/suggestions/{suggestion_id}/feedback")
def suggestion_feedback(suggestion_id: int, body: dict, db: Session = Depends(get_db)) -> dict:
    user_id = get_default_user_id(db)
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
    db.commit()
    return {"status": "updated"}
