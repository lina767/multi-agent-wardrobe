from app.agents.wardrobe_agent import WardrobeAgent


def test_gap_analysis_returns_structured_fields_and_impact() -> None:
    items = [
        {"id": 1, "name": "White Tee", "category": "top", "style_tags": ["minimalist"], "season_tags": ["spring"], "is_available": True, "status": "clean"},
        {"id": 2, "name": "Blue Shirt", "category": "top", "style_tags": ["classic"], "season_tags": ["spring"], "is_available": True, "status": "clean"},
        {"id": 3, "name": "Navy Pants", "category": "bottom", "style_tags": ["classic"], "season_tags": ["spring"], "is_available": True, "status": "clean"},
        {"id": 4, "name": "Black Jeans", "category": "bottom", "style_tags": ["minimalist"], "season_tags": ["autumn"], "is_available": True, "status": "clean"},
        {"id": 5, "name": "White Sneakers", "category": "shoes", "style_tags": ["minimalist"], "season_tags": ["spring"], "is_available": True, "status": "clean"},
    ]
    result = WardrobeAgent().analyze_wardrobe(items, color_profile={"palette": ["schwarz"]})
    gap = result["gap_analysis"][0]
    assert "target_item_archetype" in gap
    assert "suggested_color" in gap
    assert isinstance(gap["upgrade_count"], int)
    assert isinstance(gap["estimated_new_outfits"], int)
    assert isinstance(gap["impacted_item_ids"], list)
    assert 0.0 <= float(gap["confidence"]) <= 1.0
    assert gap["upgrade_count"] >= 0


def test_wardrobe_analytics_endpoint_exposes_extended_gap_payload(client) -> None:
    rows = [
        {"name": "White shirt", "category": "top"},
        {"name": "Gray trousers", "category": "bottom"},
        {"name": "Black sneakers", "category": "shoes"},
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
                "is_available": True,
                "status": "clean",
                "style_tags": ["classic"],
            },
        )
        assert create.status_code == 201

    response = client.get("/api/v1/wardrobe/analytics")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("gap_analysis"), list)
    gap = payload["gap_analysis"][0]
    assert "target_item_archetype" in gap
    assert "suggested_color" in gap
    assert "upgrade_count" in gap
    assert "impacted_item_ids" in gap
    assert "confidence" in gap
