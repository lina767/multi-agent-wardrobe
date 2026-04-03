import io
from unittest.mock import AsyncMock, patch

from app.db import session as session_module
from app.db.models import WardrobeItem
from app.services import vision_pipeline as vision_pipeline_module
from app.services.hf_vision_service import (
    VisionTags,
    _map_category,
    _map_color_families,
    _map_material,
    _map_style_tags,
)


def test_hf_label_mapping_to_domain_values() -> None:
    assert _map_category("shirt") == "top"
    assert _map_category("jeans") == "bottom"
    assert _map_category("unknown") is None
    assert _map_color_families(["black", "blue"]) == ["neutral", "cool"]
    assert _map_style_tags(["casual", "avant-garde"]) == ["casual"]
    assert _map_material("wool") == "wool"
    assert _map_material("suede") is None


def test_upload_sets_pending_and_enqueues(client, monkeypatch) -> None:
    create = client.post(
        "/api/v1/wardrobe/items",
        json={
            "name": "Vision Tee",
            "category": "top",
            "color_families": ["neutral"],
            "formality": "casual",
            "season_tags": [],
            "is_available": True,
            "style_tags": [],
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    called: dict[str, int | None] = {"item_id": None}

    async def _fake_enqueue(item_id: int, image_bytes: bytes, extension: str) -> None:
        called["item_id"] = item_id
        assert image_bytes
        assert extension == "png"

    monkeypatch.setattr(vision_pipeline_module.settings, "vision_enabled", True)
    monkeypatch.setattr(vision_pipeline_module.vision_pipeline, "enqueue", _fake_enqueue)

    files = {"image": ("tee.png", io.BytesIO(b"fakepngdata"), "image/png")}
    up = client.post(f"/api/v1/wardrobe/items/{item_id}/image", files=files)
    assert up.status_code == 200
    body = up.json()
    assert body["vision_status"] == "pending"
    assert body["vision_error"] is None
    assert called["item_id"] == item_id


def test_worker_marks_done_and_updates_fields(monkeypatch) -> None:
    db = session_module.SessionLocal()
    row = WardrobeItem(
        user_id=1,
        name="Worker Tee",
        category="top",
        color_families_json=["neutral"],
        formality="casual",
        season_tags_json=[],
        weather_tags_json=[],
        is_available=True,
        status="clean",
        style_tags_json=[],
        image_path="uploads/raw.png",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    db.close()

    class _StubService:
        async def predict_tags(self, image_bytes: bytes) -> VisionTags:
            return VisionTags(
                category="outer",
                color_families=["earth"],
                dominant_colors=[],
                style_tags=["classic"],
                material="wool",
            )

        async def remove_background(self, image_bytes: bytes) -> bytes:
            return b"png"

    monkeypatch.setattr(vision_pipeline_module.vision_pipeline, "_service", _StubService())

    job = vision_pipeline_module.VisionJob(item_id=row.id, image_bytes=b"raw", extension="png")
    import asyncio

    asyncio.run(vision_pipeline_module.vision_pipeline._process_job(job))

    db = session_module.SessionLocal()
    updated = db.query(WardrobeItem).filter(WardrobeItem.id == row.id).first()
    assert updated is not None
    assert updated.vision_status == "done"
    assert updated.category == "outer"
    assert updated.color_families_json == ["earth"]
    assert updated.style_tags_json == ["classic"]
    assert updated.material == "wool"
    assert updated.processed_image_path is not None
    db.close()


def test_predict_tags_falls_back_to_claude_when_hf_fails(monkeypatch) -> None:
    db = session_module.SessionLocal()
    row = WardrobeItem(
        user_id=1,
        name="Fallback Tee",
        category="top",
        color_families_json=["neutral"],
        formality="casual",
        season_tags_json=[],
        weather_tags_json=[],
        is_available=True,
        status="clean",
        style_tags_json=[],
        image_path="uploads/raw.png",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    db.close()

    class _FailingHf:
        def is_configured(self) -> bool:
            return True

        async def predict_tags(self, image_bytes: bytes) -> VisionTags:
            raise RuntimeError("HF down")

        async def remove_background(self, image_bytes: bytes) -> bytes:
            return b"png"

    fallback_tags = VisionTags(
        category="bottom",
        color_families=["cool"],
        dominant_colors=[],
        style_tags=["casual"],
        material="cotton",
    )

    monkeypatch.setattr(vision_pipeline_module.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(vision_pipeline_module.vision_pipeline, "_service", _FailingHf())
    monkeypatch.setattr(
        vision_pipeline_module,
        "predict_wardrobe_tags_anthropic",
        AsyncMock(return_value=fallback_tags),
    )

    job = vision_pipeline_module.VisionJob(item_id=row.id, image_bytes=b"raw", extension="png")
    import asyncio

    asyncio.run(vision_pipeline_module.vision_pipeline._process_job(job))

    db = session_module.SessionLocal()
    updated = db.query(WardrobeItem).filter(WardrobeItem.id == row.id).first()
    assert updated is not None
    assert updated.vision_status == "done"
    assert updated.category == "bottom"
    assert updated.color_families_json == ["cool"]
    assert updated.material == "cotton"
    db.close()
