from datetime import UTC, datetime, timedelta

from app.db.models import FeedbackEvent
from app.models.profile import StyleSignalEvent
from app.services.temporal_intelligence import (
    _build_embedding_from_signals,
    _compute_offline_metrics,
    _derive_dynamic_weights,
    _estimate_change_point,
    parse_item_ids,
)


def _signal(
    *,
    sid: int,
    occurred_at: datetime,
    signal_type: str = "suggestion_feedback",
    source: str = "api",
    payload: dict | None = None,
    weight: float = 1.0,
) -> StyleSignalEvent:
    return StyleSignalEvent(
        id=sid,
        user_id=1,
        signal_type=signal_type,
        source=source,
        payload_json=payload or {},
        weight=weight,
        occurred_at=occurred_at,
    )


def test_derive_dynamic_weights_prioritizes_context_when_needed() -> None:
    weights = _derive_dynamic_weights(
        fit_confidence=0.3,
        acceptance_ratio=0.2,
        dominant_occasion="work",
    )
    assert abs(sum(weights.values()) - 1.0) < 0.001
    assert weights["context_fit"] > weights["style_fit"]


def test_estimate_change_point_returns_zero_for_small_samples() -> None:
    now = datetime.now(UTC)
    signals = [
        _signal(sid=1, occurred_at=now - timedelta(days=1), payload={"style_goals": ["minimal"]}),
        _signal(sid=2, occurred_at=now - timedelta(days=2), payload={"style_goals": ["minimal"]}),
    ]
    assert _estimate_change_point(signals) == 0.0


def test_estimate_change_point_detects_goal_shift() -> None:
    now = datetime.now(UTC)
    recent = [
        _signal(sid=i, occurred_at=now - timedelta(days=i), payload={"style_goals": ["tailored", "polished"]})
        for i in range(1, 9)
    ]
    older = [
        _signal(sid=100 + i, occurred_at=now - timedelta(days=20 + i), payload={"style_goals": ["streetwear"]})
        for i in range(1, 9)
    ]
    score = _estimate_change_point(recent + older)
    assert score > 0.4


def test_build_embedding_from_signals_normalizes_style_and_occasion() -> None:
    now = datetime.now(UTC)
    signals = [
        _signal(
            sid=1,
            occurred_at=now - timedelta(days=1),
            payload={"style_goals": ["minimal", "classic"], "occasion": "work"},
            source="checkin",
            weight=0.9,
        ),
        _signal(
            sid=2,
            occurred_at=now - timedelta(days=4),
            payload={"style_goals": ["minimal"], "occasion": "casual"},
            source="feedback",
            weight=0.6,
        ),
    ]
    embedding = _build_embedding_from_signals(signals, half_life_days=3, now=now)
    assert "style_goal_weights" in embedding
    assert "occasion_weights" in embedding
    assert embedding["style_goal_weights"]["minimal"] > 0
    assert 0.0 <= embedding["stability_score"] <= 1.0


def test_compute_offline_metrics_and_parse_item_ids() -> None:
    now = datetime.now(UTC)
    signals = [
        _signal(sid=1, occurred_at=now, payload={"accepted": True}, source="a"),
        _signal(sid=2, occurred_at=now, payload={"accepted": False}, source="b"),
    ]
    feedback = [FeedbackEvent(user_id=1, suggestion_item_ids_json="[1,2,3]", rating=4, comment=None)]
    metrics = _compute_offline_metrics(signals=signals, feedback=feedback)
    assert 0.0 <= metrics["acceptance_rate"] <= 1.0
    assert metrics["mean_rating"] == 4.0

    assert parse_item_ids("[1, \"2\", \"x\"]") == [1, 2]
    assert parse_item_ids("not-json") == []
    assert parse_item_ids("{\"a\":1}") == []
