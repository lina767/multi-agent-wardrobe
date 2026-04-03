from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.schemas import WardrobeItemCreate, WardrobeItemRead, WardrobeItemUpdate
from app.agents.wardrobe_agent import WardrobeAgent
from app.config import settings
from app.db.models import WardrobeItem
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.domain.enums import ColorFamily, DresscodeLevel, FitType, ItemCondition, ItemStatus, MaterialType, WardrobeCategory, WearFrequency
from app.models.profile import UserProfile
from app.services.temporal_intelligence import record_style_signal
from app.services.vision_pipeline import vision_pipeline
from app.storage import delete_image, resolve_image_url, upload_image

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"}
_MATERIAL_INSIGHTS: dict[str, dict[str, str]] = {
    MaterialType.COTTON.value: {
        "care": "Machine wash at low to medium heat; avoid over-drying.",
        "weather": "Breathable and versatile in mild to warm weather.",
        "texture_match": "Works well with denim, knitwear, and matte textures.",
    },
    MaterialType.SILK.value: {
        "care": "Use delicate cycle or hand wash; avoid high heat and friction.",
        "weather": "Lightweight and cool for warm weather, but layers well.",
        "texture_match": "Pairs best with soft knits, fine wool, and polished fabrics.",
    },
    MaterialType.WOOL.value: {
        "care": "Hand wash or wool cycle; lay flat to dry to preserve shape.",
        "weather": "Insulating and warm for cool to cold weather.",
        "texture_match": "Balances smooth fabrics and adds depth to layered looks.",
    },
    MaterialType.SYNTHETIC.value: {
        "care": "Wash cool and avoid high dryer heat to prevent fiber damage.",
        "weather": "Durable and often weather-resistant; varies by blend.",
        "texture_match": "Good with technical fabrics and structured outerwear.",
    },
    MaterialType.LINEN.value: {
        "care": "Wash cool and air dry when possible; steam to relax wrinkles.",
        "weather": "Cool and airy, ideal for warm weather.",
        "texture_match": "Great with cotton and lightweight textured layers.",
    },
}

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None
try:
    from pillow_heif import register_heif_opener
except Exception:  # pragma: no cover
    register_heif_opener = None


def _normalize_upload_payload(payload: bytes, extension: str) -> tuple[bytes, str]:
    ext = extension.lower().lstrip(".")
    if ext not in {"heic", "heif"}:
        return payload, ext


def _material_insights(material: str | None) -> dict[str, str] | None:
    if not material:
        return None
    return _MATERIAL_INSIGHTS.get(material.strip().lower())


def _parse_material(material: str | None) -> MaterialType | None:
    if not material:
        return None
    value = material.strip().lower()
    try:
        return MaterialType(value)
    except ValueError:
        return None
    if Image is None or register_heif_opener is None:
        # Accept HEIC as-is when conversion libs are unavailable.
        return payload, ext
    try:
        register_heif_opener()
        with Image.open(BytesIO(payload)) as image:
            rgb = image.convert("RGB")
            out = BytesIO()
            rgb.save(out, format="JPEG", quality=92)
        return out.getvalue(), "jpg"
    except Exception:
        # Keep upload path resilient; fallback to original bytes/ext.
        return payload, ext


@router.get("/items", response_model=list[WardrobeItemRead])
def list_items(
    category: str | None = Query(default=None),
    color_family: str | None = Query(default=None),
    weather_tag: str | None = Query(default=None),
    status_filter: ItemStatus | None = Query(default=None, alias="status"),
    condition_filter: ItemCondition | None = Query(default=None, alias="condition"),
    wear_frequency_filter: WearFrequency | None = Query(default=None, alias="wear_frequency"),
    fit_type_filter: FitType | None = Query(default=None, alias="fit_type"),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc"),
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> list[WardrobeItemRead]:
    query = db.query(WardrobeItem).filter(WardrobeItem.user_id == uid)
    if category:
        query = query.filter(WardrobeItem.category == category)
    rows = query.all()
    if color_family:
        rows = [row for row in rows if color_family in (row.color_families_json or [])]
    if weather_tag:
        rows = [row for row in rows if weather_tag in (row.weather_tags_json or [])]
    if status_filter:
        rows = [row for row in rows if (row.status or ItemStatus.CLEAN.value) == status_filter.value]
    if condition_filter:
        rows = [row for row in rows if (row.condition or ItemCondition.GOOD.value) == condition_filter.value]
    if wear_frequency_filter:
        rows = [row for row in rows if (row.wear_frequency or WearFrequency.SOMETIMES.value) == wear_frequency_filter.value]
    if fit_type_filter:
        rows = [row for row in rows if (row.fit_type or FitType.REGULAR.value) == fit_type_filter.value]
    reverse = sort_dir.lower() == "desc"
    if sort_by == "name":
        rows.sort(key=lambda row: row.name.lower(), reverse=reverse)
    else:
        rows.sort(key=lambda row: row.id, reverse=reverse)
    return [_serialize_row(r) for r in rows]


@router.post("/items", response_model=WardrobeItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    body: WardrobeItemCreate,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> WardrobeItemRead:
    row = WardrobeItem(
        user_id=uid,
        name=body.name,
        category=body.category.value,
        color_families_json=[c.value for c in body.color_families],
        dominant_colors_json=[entry.model_dump() for entry in body.dominant_colors],
        formality=body.formality.value,
        season_tags_json=body.season_tags,
        weather_tags_json=body.weather_tags,
        is_available=body.is_available,
        status=body.status.value,
        style_tags_json=body.style_tags,
        brand=body.brand,
        size_label=body.size_label,
        fit_type=body.fit_type.value,
        material=body.material.value if body.material else None,
        wear_frequency=body.wear_frequency.value,
        last_worn_at=body.last_worn_at,
        condition=body.condition.value,
        quantity=body.quantity,
        purchase_price=body.purchase_price,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_row(row)


@router.patch("/items/{item_id}", response_model=WardrobeItemRead)
def update_item(
    item_id: int,
    body: WardrobeItemUpdate,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> WardrobeItemRead:
    row = db.query(WardrobeItem).filter(WardrobeItem.id == item_id, WardrobeItem.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    data = body.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is not None:
        data["category"] = data["category"].value
    if "color_families" in data and data["color_families"] is not None:
        data["color_families_json"] = [c.value for c in data.pop("color_families")]
    if "dominant_colors" in data and data["dominant_colors"] is not None:
        data["dominant_colors_json"] = data.pop("dominant_colors")
    if "formality" in data and data["formality"] is not None:
        data["formality"] = data["formality"].value
    if "status" in data and data["status"] is not None:
        data["status"] = data["status"].value
    if "fit_type" in data and data["fit_type"] is not None:
        data["fit_type"] = data["fit_type"].value
    if "material" in data and data["material"] is not None:
        data["material"] = data["material"].value
    if "wear_frequency" in data and data["wear_frequency"] is not None:
        data["wear_frequency"] = data["wear_frequency"].value
    if "condition" in data and data["condition"] is not None:
        data["condition"] = data["condition"].value
    if "season_tags" in data and data["season_tags"] is not None:
        data["season_tags_json"] = data.pop("season_tags")
    if "weather_tags" in data and data["weather_tags"] is not None:
        data["weather_tags_json"] = data.pop("weather_tags")
    if "style_tags" in data and data["style_tags"] is not None:
        data["style_tags_json"] = data.pop("style_tags")
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _serialize_row(row)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> None:
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
    uid: int = Depends(get_current_user_id),
) -> WardrobeItemRead:
    row = db.query(WardrobeItem).filter(WardrobeItem.id == item_id, WardrobeItem.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if not image.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = image.filename.split(".")[-1].lower() if "." in image.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {ext}")

    payload = await image.read()
    payload, ext = _normalize_upload_payload(payload, ext)
    try:
        image_ref = upload_image(row.id, payload, ext)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if row.image_path:
        delete_image(row.image_path)
    row.image_path = image_ref
    row.vision_status = "pending"
    row.vision_error = None
    row.processed_image_path = None
    db.commit()
    db.refresh(row)
    if settings.vision_enabled:
        await vision_pipeline.enqueue(item_id=row.id, image_bytes=payload, extension=ext)
    return _serialize_row(row)


@router.post("/bulk-upload")
async def bulk_upload_items(
    images: list[UploadFile] = File(...),
    analyze: bool = Form(True),
    category: str = Form("top"),
    formality: str = Form("casual"),
    color_family: str = Form("neutral"),
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> dict:
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    try:
        parsed_category = WardrobeCategory(category).value
        parsed_formality = DresscodeLevel(formality).value
        parsed_color = ColorFamily(color_family).value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid bulk-upload defaults") from exc

    created_rows: list[WardrobeItem] = []
    vision_inputs: list[tuple[int, bytes, str]] = []
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
            dominant_colors_json=[],
            formality=parsed_formality,
            season_tags_json=[],
            weather_tags_json=[],
            is_available=True,
            status=ItemStatus.CLEAN.value,
            style_tags_json=[],
            quantity=1,
        )
        db.add(row)
        db.flush()

        payload = await image.read()
        payload, ext = _normalize_upload_payload(payload, ext)
        try:
            image_ref = upload_image(row.id, payload, ext)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        row.image_path = image_ref
        vision_inputs.append((row.id, payload, ext))
        row.vision_status = "pending"
        row.vision_error = None
        row.processed_image_path = None
        created_rows.append(row)

    db.commit()
    for row in created_rows:
        db.refresh(row)
    if settings.vision_enabled:
        for item_id, payload, ext in vision_inputs:
            if payload:
                await vision_pipeline.enqueue(item_id=item_id, image_bytes=payload, extension=ext)

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
                "dominant_colors": list(r.dominant_colors_json or []),
                "is_available": r.is_available,
                "status": r.status or ItemStatus.CLEAN.value,
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
        dominant_colors=list(row.dominant_colors_json or []),
        formality=DresscodeLevel(row.formality),
        season_tags=list(row.season_tags_json or []),
        weather_tags=list(row.weather_tags_json or []),
        is_available=row.is_available,
        status=ItemStatus(row.status or ItemStatus.CLEAN.value),
        style_tags=list(row.style_tags_json or []),
        brand=row.brand,
        size_label=row.size_label,
        fit_type=FitType(row.fit_type or FitType.REGULAR.value),
        material=_parse_material(row.material),
        wear_frequency=WearFrequency(row.wear_frequency or WearFrequency.SOMETIMES.value),
        last_worn_at=row.last_worn_at,
        condition=ItemCondition(row.condition or ItemCondition.GOOD.value),
        quantity=row.quantity,
        purchase_price=row.purchase_price,
        notes=row.notes,
        image_url=resolve_image_url(row.image_path),
        processed_image_url=resolve_image_url(row.processed_image_path),
        vision_status=row.vision_status or "pending",
        vision_error=row.vision_error,
        material_insights=_material_insights(row.material),
    )
