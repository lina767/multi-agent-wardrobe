import io

from fastapi.testclient import TestClient


def _seed_wardrobe(client: TestClient) -> None:
    items = [
        {
            "name": "White shirt",
            "category": "top",
            "color_families": ["neutral"],
            "formality": "business",
            "season_tags": [],
            "is_available": True,
            "style_tags": ["classic"],
        },
        {
            "name": "Navy trousers",
            "category": "bottom",
            "color_families": ["cool"],
            "formality": "business",
            "season_tags": [],
            "is_available": True,
            "style_tags": ["classic"],
        },
        {
            "name": "Black loafers",
            "category": "shoes",
            "color_families": ["neutral"],
            "formality": "smart_casual",
            "season_tags": [],
            "is_available": True,
            "style_tags": ["minimalist"],
        },
    ]
    for it in items:
        r = client.post("/v1/wardrobe/items", json=it)
        assert r.status_code == 201


def test_health(client: TestClient) -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_recommendations_top3_with_evidence(client: TestClient) -> None:
    _seed_wardrobe(client)
    body = {
        "context": {
            "temperature_c": 12.0,
            "event_type": "meeting",
            "mood": "focus",
        },
        "palette_bias": ["cool"],
        "max_candidates_to_rank": 30,
    }
    r = client.post("/v1/recommendations", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["suggestions"]) >= 1
    s0 = data["suggestions"][0]
    assert len(s0["evidence_tags"]) >= 2
    assert s0["total_score"] > 0
    assert "White shirt" in s0["item_names"] or "Navy" in " ".join(s0["item_names"])


def test_feedback_roundtrip(client: TestClient) -> None:
    r = client.post("/v1/feedback", json={"suggestion_item_ids": [1, 2, 3], "rating": 5})
    assert r.status_code == 201
    lst = client.get("/v1/feedback")
    assert lst.status_code == 200
    assert len(lst.json()) >= 1


def test_wardrobe_patch_and_delete(client: TestClient) -> None:
    r = client.post(
        "/v1/wardrobe/items",
        json={
            "name": "Tee",
            "category": "top",
            "color_families": ["warm"],
            "formality": "casual",
            "season_tags": [],
            "is_available": True,
            "style_tags": [],
        },
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    u = client.patch(f"/v1/wardrobe/items/{iid}", json={"name": "Tee updated"})
    assert u.status_code == 200
    assert u.json()["name"] == "Tee updated"
    d = client.delete(f"/v1/wardrobe/items/{iid}")
    assert d.status_code == 204


def test_recommendations_empty_wardrobe(client: TestClient) -> None:
    r = client.post(
        "/v1/recommendations",
        json={"context": {"event_type": "home"}, "max_candidates_to_rank": 20},
    )
    assert r.status_code == 200
    assert r.json()["suggestions"] == []


def test_upload_inventory_image(client: TestClient) -> None:
    create = client.post(
        "/v1/wardrobe/items",
        json={
            "name": "Image Tee",
            "category": "top",
            "color_families": ["neutral"],
            "formality": "casual",
            "season_tags": [],
            "is_available": True,
            "style_tags": [],
        },
    )
    assert create.status_code == 201
    iid = create.json()["id"]

    files = {"image": ("tee.png", io.BytesIO(b"fakepngdata"), "image/png")}
    up = client.post(f"/v1/wardrobe/items/{iid}/image", files=files)
    assert up.status_code == 200
    body = up.json()
    assert body["image_url"] is not None
    assert body["image_url"].startswith("/media/uploads/")


def test_recommendation_pipeline_integration_deterministic_and_evidence(client: TestClient) -> None:
    items = [
        ("White shirt", "top", "business", ["neutral"], ["classic"]),
        ("Blue oxford", "top", "business", ["cool"], ["classic"]),
        ("Black tee", "top", "casual", ["neutral"], ["minimalist"]),
        ("Navy trousers", "bottom", "business", ["cool"], ["classic"]),
        ("Gray chinos", "bottom", "smart_casual", ["neutral"], ["versatile"]),
        ("Tailored blazer", "outer", "business", ["neutral"], ["classic"]),
        ("Wool coat", "outer", "formal", ["neutral"], ["minimalist"]),
        ("Black loafers", "shoes", "business", ["neutral"], ["classic"]),
        ("White sneakers", "shoes", "casual", ["neutral"], ["minimalist"]),
        ("Silver watch", "accessory", "smart_casual", ["cool"], ["versatile"]),
    ]
    for name, cat, formality, colors, tags in items:
        r = client.post(
            "/v1/wardrobe/items",
            json={
                "name": name,
                "category": cat,
                "color_families": colors,
                "formality": formality,
                "season_tags": ["spring", "autumn"],
                "is_available": True,
                "style_tags": tags,
            },
        )
        assert r.status_code == 201

    body = {
        "context": {"temperature_c": 14, "event_type": "meeting", "mood": "power"},
        "palette_bias": ["neutral", "cool"],
        "max_candidates_to_rank": 60,
    }
    first = client.post("/v1/recommendations", json=body)
    second = client.post("/v1/recommendations", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    data1 = first.json()["suggestions"]
    data2 = second.json()["suggestions"]
    assert len(data1) >= 1
    assert [s["item_ids"] for s in data1] == [s["item_ids"] for s in data2]
    assert [s["total_score"] for s in data1] == [s["total_score"] for s in data2]
    for suggestion in data1:
        assert len(suggestion["evidence_tags"]) >= 2
    assert any(any(tag["evidence_id"] == "enclothed_cognition" for tag in s["evidence_tags"]) for s in data1)
