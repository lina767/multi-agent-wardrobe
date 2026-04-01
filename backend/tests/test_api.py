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
            "status": "clean",
            "style_tags": ["classic"],
        },
        {
            "name": "Navy trousers",
            "category": "bottom",
            "color_families": ["cool"],
            "formality": "business",
            "season_tags": [],
            "is_available": True,
            "status": "clean",
            "style_tags": ["classic"],
        },
        {
            "name": "Black loafers",
            "category": "shoes",
            "color_families": ["neutral"],
            "formality": "smart_casual",
            "season_tags": [],
            "is_available": True,
            "status": "clean",
            "style_tags": ["minimalist"],
        },
    ]
    for it in items:
        r = client.post("/api/v1/wardrobe/items", json=it)
        assert r.status_code == 201


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_embeddings_endpoint_returns_vector(client: TestClient) -> None:
    r = client.post("/api/v1/embeddings", json={"input": "minimalist business casual outfit"})
    assert r.status_code == 200
    payload = r.json()
    assert "data" in payload and len(payload["data"]) == 1
    emb = payload["data"][0]["embedding"]
    assert isinstance(emb, list)
    assert len(emb) == 256


def test_auth_me_returns_current_user(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "test-user@example.com"
    assert payload["is_active"] is True


def test_wardrobe_requires_auth(unauth_client: TestClient) -> None:
    response = unauth_client.get("/api/v1/wardrobe/items")
    assert response.status_code == 401


def test_legacy_health_alias(client: TestClient) -> None:
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
    r = client.post("/api/v1/recommendations", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["suggestions"]) >= 1
    s0 = data["suggestions"][0]
    assert len(s0["evidence_tags"]) >= 2
    assert s0["total_score"] > 0
    assert "White shirt" in s0["item_names"] or "Navy" in " ".join(s0["item_names"])


def test_feedback_roundtrip(client: TestClient) -> None:
    r = client.post("/api/v1/feedback", json={"suggestion_item_ids": [1, 2, 3], "rating": 5})
    assert r.status_code == 201
    lst = client.get("/api/v1/feedback")
    assert lst.status_code == 200
    assert len(lst.json()) >= 1


def test_wardrobe_patch_and_delete(client: TestClient) -> None:
    r = client.post(
        "/api/v1/wardrobe/items",
        json={
            "name": "Tee",
            "category": "top",
            "color_families": ["warm"],
            "formality": "casual",
            "season_tags": [],
            "is_available": True,
            "status": "clean",
            "style_tags": [],
        },
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    u = client.patch(f"/api/v1/wardrobe/items/{iid}", json={"name": "Tee updated", "status": "dirty"})
    assert u.status_code == 200
    assert u.json()["name"] == "Tee updated"
    assert u.json()["status"] == "dirty"
    d = client.delete(f"/api/v1/wardrobe/items/{iid}")
    assert d.status_code == 204


def test_recommendations_empty_wardrobe(client: TestClient) -> None:
    r = client.post(
        "/api/v1/recommendations",
        json={"context": {"event_type": "home"}, "max_candidates_to_rank": 20},
    )
    assert r.status_code == 200
    assert r.json()["suggestions"] == []


def test_recommendations_exclude_dirty_and_dry_cleaning_items(client: TestClient) -> None:
    rows = [
        {"name": "Clean top", "category": "top", "status": "clean"},
        {"name": "Dirty top", "category": "top", "status": "dirty"},
        {"name": "Clean bottom", "category": "bottom", "status": "clean"},
        {"name": "Dry-clean shoes", "category": "shoes", "status": "dry_cleaning"},
        {"name": "Clean shoes", "category": "shoes", "status": "clean"},
    ]
    for row in rows:
        create = client.post(
            "/api/v1/wardrobe/items",
            json={
                "name": row["name"],
                "category": row["category"],
                "color_families": ["neutral"],
                "formality": "casual",
                "season_tags": [],
                "weather_tags": [],
                "is_available": True,
                "status": row["status"],
                "style_tags": [],
            },
        )
        assert create.status_code == 201

    r = client.post(
        "/api/v1/recommendations",
        json={"context": {"event_type": "home"}, "max_candidates_to_rank": 20},
    )
    assert r.status_code == 200
    suggestions = r.json()["suggestions"]
    assert len(suggestions) >= 1
    for suggestion in suggestions:
        assert "Dirty top" not in suggestion["item_names"]
        assert "Dry-clean shoes" not in suggestion["item_names"]


def test_upload_inventory_image(client: TestClient) -> None:
    create = client.post(
        "/api/v1/wardrobe/items",
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
    up = client.post(f"/api/v1/wardrobe/items/{iid}/image", files=files)
    assert up.status_code == 200
    body = up.json()
    assert body["image_url"] is not None
    assert body["image_url"].startswith("/media/uploads/")


def test_upload_inventory_image_accepts_heic_extension(client: TestClient) -> None:
    create = client.post(
        "/api/v1/wardrobe/items",
        json={
            "name": "HEIC Top",
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

    files = {"image": ("top.heic", io.BytesIO(b"fakeheicdata"), "image/heic")}
    up = client.post(f"/api/v1/wardrobe/items/{iid}/image", files=files)
    assert up.status_code == 200
    body = up.json()
    assert body["image_url"] is not None
    assert body["image_url"].startswith("/media/uploads/")


def test_bulk_upload_and_analysis(client: TestClient) -> None:
    files = [
        ("images", ("black_tee.png", io.BytesIO(b"fakepngdata1"), "image/png")),
        ("images", ("blue_jeans.png", io.BytesIO(b"fakepngdata2"), "image/png")),
        ("images", ("white_sneakers.png", io.BytesIO(b"fakepngdata3"), "image/png")),
    ]
    data = {"analyze": "true", "category": "top", "formality": "casual", "color_family": "neutral"}
    response = client.post("/api/v1/wardrobe/bulk-upload", files=files, data=data)
    assert response.status_code == 200
    body = response.json()
    assert body["uploaded_count"] == 3
    assert len(body["items"]) == 3
    assert body["analysis"] is not None
    assert "outfit_potential" in body["analysis"]


def test_bulk_upload_accepts_heic_extension(client: TestClient) -> None:
    files = [("images", ("shirt.heic", io.BytesIO(b"fakeheicbulk"), "image/heic"))]
    data = {"analyze": "false", "category": "top", "formality": "casual", "color_family": "neutral"}
    response = client.post("/api/v1/wardrobe/bulk-upload", files=files, data=data)
    assert response.status_code == 200
    body = response.json()
    assert body["uploaded_count"] == 1


def test_profile_checkin_and_state(client: TestClient) -> None:
    create = client.post(
        "/api/v1/profile/checkins",
        json={
            "schema_version": "v1",
            "life_phase": "professional",
            "role_transition": "student -> professional",
            "fit_confidence": 0.4,
            "style_goals": ["minimalist", "business-casual"],
        },
    )
    assert create.status_code == 200
    payload = create.json()
    assert payload["schema_version"] == "v1"
    assert payload["life_phase"] == "professional"

    listing = client.get("/api/v1/profile/checkins")
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    state = client.get("/api/v1/profile/state")
    assert state.status_code == 200
    body = state.json()
    assert body["state_key"] == "current"
    assert "dynamic_weights" in body
    assert 0 <= body["confidence"] <= 1


def test_profile_state_without_checkins_still_available(client: TestClient) -> None:
    response = client.get("/api/v1/profile/state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["state_key"] == "current"
    assert "features" in payload
    assert "dynamic_weights" in payload


def test_suggestions_include_temporal_style_profile(client: TestClient) -> None:
    _seed_wardrobe(client)
    checkin = client.post(
        "/api/v1/profile/checkins",
        json={
            "schema_version": "v1",
            "life_phase": "career-shift",
            "style_goals": ["polished", "comfort"],
            "fit_confidence": 0.5,
        },
    )
    assert checkin.status_code == 200
    response = client.get("/api/v1/suggestions?mood=focus&occasion=smart%20casual")
    assert response.status_code == 200
    body = response.json()
    assert "style_profile" in body
    assert "temporal_state" in body["style_profile"]
    assert "dynamic_weights" in body["style_profile"]
    weights = body["style_profile"]["dynamic_weights"]
    assert "context_fit" in weights
    assert 0 <= float(weights["context_fit"]) <= 1


def test_suggestions_include_temporal_state_when_no_checkin(client: TestClient) -> None:
    _seed_wardrobe(client)
    response = client.get("/api/v1/suggestions?mood=focus&occasion=casual")
    assert response.status_code == 200
    body = response.json()
    temporal = body["style_profile"]["temporal_state"]
    assert "life_phase" in temporal
    assert "state_factors" in temporal


def test_suggestions_requires_wardrobe_items(client: TestClient) -> None:
    response = client.get("/api/v1/suggestions?mood=focus&occasion=smart%20casual")
    assert response.status_code == 400
    assert "No wardrobe items found" in response.json()["detail"]


def test_outfit_log_and_suggestion_feedback_flow(client: TestClient) -> None:
    _seed_wardrobe(client)
    suggestions = client.get("/api/v1/suggestions?mood=focus&occasion=smart%20casual")
    assert suggestions.status_code == 200
    first_suggestion_id = suggestions.json()["suggestions"][0]["id"]

    log_response = client.post(
        "/api/v1/outfits/log",
        json={"item_ids": [1, 2, 3], "occasion": "smart casual", "mood": "focus", "style_goals": ["minimalist"]},
    )
    assert log_response.status_code == 200
    assert log_response.json()["status"] == "logged"

    feedback_response = client.post(
        f"/api/v1/suggestions/{first_suggestion_id}/feedback",
        json={"accepted": True, "rating": 5, "occasion": "smart casual"},
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["status"] == "updated"


def test_suggestion_feedback_returns_404_for_missing_id(client: TestClient) -> None:
    response = client.post("/api/v1/suggestions/99999/feedback", json={"accepted": True, "rating": 4})
    assert response.status_code == 404
    assert response.json()["detail"] == "Suggestion not found"


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
            "/api/v1/wardrobe/items",
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
    first = client.post("/api/v1/recommendations", json=body)
    second = client.post("/api/v1/recommendations", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    data1 = first.json()["suggestions"]
    data2 = second.json()["suggestions"]
    assert len(data1) >= 1
    assert [s["item_ids"] for s in data1] == [s["item_ids"] for s in data2]
    assert [s["total_score"] for s in data1] == [s["total_score"] for s in data2]
    for suggestion in data1:
        assert len(suggestion["evidence_tags"]) >= 2
        trace_types = [entry.get("type") for entry in suggestion["decision_trace"] if isinstance(entry, dict)]
        assert "agent_contract" in trace_types
    assert any(any(tag["evidence_id"] == "enclothed_cognition" for tag in s["evidence_tags"]) for s in data1)


def test_profile_color_feedback_roundtrip(client: TestClient) -> None:
    body = {
        "source": "user",
        "predicted_season": "true_summer",
        "predicted_undertone": "cool",
        "predicted_contrast_level": "medium",
        "predicted_confidence": 0.72,
        "corrected_season": "cool_winter",
        "corrected_undertone": "cool",
        "corrected_contrast_level": "high",
        "note": "I wear deep cool shades best.",
    }
    response = client.post("/api/v1/profile/color-feedback", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_season"] == "true_summer"
    assert payload["corrected_season"] == "cool_winter"


def test_profile_me_update_and_readback(client: TestClient) -> None:
    initial = client.get("/api/v1/profile/me")
    assert initial.status_code == 200

    update = client.patch(
        "/api/v1/profile/me",
        json={
            "name": "Lina",
            "age": 29,
            "life_phase": "career-growth",
            "cold_sensitivity": 5,
            "figure_analysis": "balanced silhouette",
        },
    )
    assert update.status_code == 200
    payload = update.json()
    assert payload["name"] == "Lina"
    assert payload["age"] == 29
    assert payload["life_phase"] == "career-growth"
    assert payload["cold_sensitivity"] == 5
    assert payload["figure_analysis"] == "balanced silhouette"

    reread = client.get("/api/v1/profile/me")
    assert reread.status_code == 200
    assert reread.json()["name"] == "Lina"
    assert reread.json()["cold_sensitivity"] == 5


def test_profile_me_rejects_invalid_cold_sensitivity(client: TestClient) -> None:
    low = client.patch("/api/v1/profile/me", json={"cold_sensitivity": 0})
    assert low.status_code == 422
    high = client.patch("/api/v1/profile/me", json={"cold_sensitivity": 6})
    assert high.status_code == 422


def test_profile_selfie_upload_sets_url(client: TestClient) -> None:
    files = {"selfie": ("selfie.png", io.BytesIO(b"fakepngdata"), "image/png")}
    response = client.post("/api/v1/profile/selfie", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["selfie_url"] is not None
    assert payload["selfie_url"].startswith("/media/profile/")


def test_onboarding_runs_agents_and_returns_top3(client: TestClient) -> None:
    _seed_wardrobe(client)
    response = client.post(
        "/api/v1/profile/onboarding",
        json={
            "name": "Lina",
            "age": 29,
            "life_phase": "new-role",
            "cold_sensitivity": 4,
            "figure_analysis": "structured shoulders",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "profile" in payload
    assert "temporal_state" in payload
    assert payload["profile"]["cold_sensitivity"] == 4
    assert len(payload["suggestions"]) <= 3


def test_onboarding_rejects_invalid_cold_sensitivity(client: TestClient) -> None:
    _seed_wardrobe(client)
    response = client.post("/api/v1/profile/onboarding", json={"cold_sensitivity": 9})
    assert response.status_code == 422


def test_settings_email_update(client: TestClient) -> None:
    response = client.patch("/api/v1/settings/email", json={"email": "new-email@example.com"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "new-email@example.com"


def test_settings_email_update_invalid_rejected(client: TestClient) -> None:
    response = client.patch("/api/v1/settings/email", json={"email": "invalid-email"})
    assert response.status_code == 400
    assert "Invalid email" in response.json()["detail"]


def test_wardrobe_weather_tags_and_filters(client: TestClient) -> None:
    create = client.post(
        "/api/v1/wardrobe/items",
        json={
            "name": "Rain Jacket",
            "category": "outer",
            "color_families": ["cool"],
            "formality": "casual",
            "season_tags": ["autumn"],
            "weather_tags": ["rain", "wind"],
            "is_available": True,
            "style_tags": ["functional"],
        },
    )
    assert create.status_code == 201
    created = create.json()
    assert "rain" in created["weather_tags"]

    filtered = client.get("/api/v1/wardrobe/items?weather_tag=rain")
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) >= 1
    assert any("rain" in row["weather_tags"] for row in rows)
