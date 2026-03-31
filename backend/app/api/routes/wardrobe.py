from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.schemas import WardrobeItemCreate, WardrobeItemRead, WardrobeItemUpdate
from app.agents.wardrobe_agent import WardrobeAgent
from app.bootstrap import get_default_user_id
from app.db.models import WardrobeItem
from app.db.session import get_db
from app.domain.enums import ColorFamily, DresscodeLevel, WardrobeCategory
from app.models.profile import UserProfile
from app.services.temporal_intelligence import record_style_signal
from app.storage import delete_image, resolve_image_url, upload_image

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


@router.get("/items", response_model=list[WardrobeItemRead])
def list_items(db: Session = Depends(get_db)) -> list[WardrobeItemRead]:
    uid = get_default_user_id(db)
    rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == uid).order_by(WardrobeItem.id).all()
    return [_serialize_row(r) for r in rows]


@router.post("/items", response_model=WardrobeItemRead, status_code=status.HTTP_201_CREATED)
def create_item(body: WardrobeItemCreate, db: Session = Depends(get_db)) -> WardrobeItemRead:
    uid = get_default_user_id(db)
    row = WardrobeItem(
        user_id=uid,
        name=body.name,
        category=body.category.value,
        color_families_json=[c.value for c in body.color_families],
        formality=body.formality.value,
        season_tags_json=body.season_tags,
        is_available=body.is_available,
        style_tags_json=body.style_tags,
        brand=body.brand,
        size_label=body.size_label,
        material=body.material,
        quantity=body.quantity,
        purchase_price=body.purchase_price,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_row(row)


@router.patch("/items/{item_id}", response_model=WardrobeItemRead)
def update_item(item_id: int, body: WardrobeItemUpdate, db: Session = Depends(get_db)) -> WardrobeItemRead:
    uid = get_default_user_id(db)
    row = db.query(WardrobeItem).filter(WardrobeItem.id == item_id, WardrobeItem.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    data = body.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is not None:
        data["category"] = data["category"].value
    if "color_families" in data and data["color_families"] is not None:
        data["color_families_json"] = [c.value for c in data.pop("color_families")]
    if "formality" in data and data["formality"] is not None:
        data["formality"] = data["formality"].value
    if "season_tags" in data and data["season_tags"] is not None:
        data["season_tags_json"] = data.pop("season_tags")
    if "style_tags" in data and data["style_tags"] is not None:
        data["style_tags_json"] = data.pop("style_tags")
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _serialize_row(row)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    uid = get_default_user_id(db)
    row = db.query(WardrobeItem).filter(WardrobeItem.id == item_id, WardrobeItem.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row.image_path:
        delete_image(row.image_path)
    db.delete(row)
    db.commit()


@router.post("/items/{item_id}/image", response_model=WardrobeItemRead)
async def upload_item_image(
    item_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> WardrobeItemRead:
    uid = get_default_user_id(db)
    row = db.query(WardrobeItem).filter(WardrobeItem.id == item_id, WardrobeItem.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if not image.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = image.filename.split(".")[-1].lower() if "." in image.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {ext}")

    payload = await image.read()
    try:
        image_ref = upload_image(row.id, payload, ext)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if row.image_path:
        delete_image(row.image_path)
    row.image_path = image_ref
    db.commit()
    db.refresh(row)
    return _serialize_row(row)


@router.post("/bulk-upload")
async def bulk_upload_items(
    images: list[UploadFile] = File(...),
    analyze: bool = Form(True),
    category: str = Form("top"),
    formality: str = Form("casual"),
    color_family: str = Form("neutral"),
    db: Session = Depends(get_db),
) -> dict:
    uid = get_default_user_id(db)
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    try:
        parsed_category = WardrobeCategory(category).value
        parsed_formality = DresscodeLevel(formality).value
        parsed_color = ColorFamily(color_family).value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid bulk-upload defaults") from exc

    created_rows: list[WardrobeItem] = []
    for image in images:
        if not image.filename:
            raise HTTPException(status_code=400, detail="Missing filename")
        ext = image.filename.split(".")[-1].lower() if "." in image.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {ext}")

        display_name = Path(image.filename).stem.replace("_", " ").replace("-", " ").strip().title()
        if not display_name:
            display_name = "Imported Item"

        row = WardrobeItem(
            user_id=uid,
            name=display_name,
            category=parsed_category,
            color_families_json=[parsed_color],
            formality=parsed_formality,
            season_tags_json=[],
            is_available=True,
            style_tags_json=[],
            quantity=1,
        )
        db.add(row)
        db.flush()

        payload = await image.read()
        try:
            image_ref = upload_image(row.id, payload, ext)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        row.image_path = image_ref
        created_rows.append(row)

    db.commit()
    for row in created_rows:
        db.refresh(row)

    analysis: dict | None = None
    if analyze:
        all_rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == uid).all()
        profile = db.query(UserProfile).filter(UserProfile.user_id == uid).first()
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
            for r in all_rows
        ]
        color_profile = {"palette": profile.color_palette} if profile and profile.color_palette else None
        analysis = WardrobeAgent().analyze_wardrobe(items, color_profile=color_profile)
    record_style_signal(
        db,
        user_id=uid,
        signal_type="wardrobe_upload",
        source="bulk_upload",
        weight=0.7,
        payload={
            "uploaded_count": len(created_rows),
            "category": parsed_category,
            "formality": parsed_formality,
            "style_goals": [],
        },
    )
    db.commit()

    return {
        "uploaded_count": len(created_rows),
        "items": [_serialize_row(row) for row in created_rows],
        "analysis": analysis,
    }


def _serialize_row(row: WardrobeItem) -> WardrobeItemRead:
    from app.domain.enums import ColorFamily, DresscodeLevel, WardrobeCategory

    return WardrobeItemRead(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        category=WardrobeCategory(row.category),
        color_families=[ColorFamily(c) for c in (row.color_families_json or [])],
        formality=DresscodeLevel(row.formality),
        season_tags=list(row.season_tags_json or []),
        is_available=row.is_available,
        style_tags=list(row.style_tags_json or []),
        brand=row.brand,
        size_label=row.size_label,
        material=row.material,
        quantity=row.quantity,
        purchase_price=row.purchase_price,
        notes=row.notes,
        image_url=resolve_image_url(row.image_path),
    )
