from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.api.schemas import ProfileCheckinCreate
from app.db.models import FeedbackEvent, OutfitLog
from app.models.profile import PreferenceEmbedding, StyleSignalEvent, UserCheckin, UserStateTimeline


class FeatureBuilder:
    def build(
        self,
        *,
        checkins: list[UserCheckin],
        signals: list[StyleSignalEvent],
        feedback: list[FeedbackEvent],
        outfit_logs: list[OutfitLog],
    ) -> dict[str, Any]:
        latest_checkin = checkins[0] if checkins else None
        life_phase = latest_checkin.life_phase if latest_checkin else "unspecified"
        role_transition = latest_checkin.role_transition if latest_checkin else None
        fit_confidence = latest_checkin.fit_confidence if latest_checkin and latest_checkin.fit_confidence is not None else 0.6
        style_goals = list(latest_checkin.style_goals_json or []) if latest_checkin else []

        accepted = sum(
            1 for s in signals if s.signal_type in {"suggestion_feedback", "manual_feedback"} and bool(s.payload_json.get("accepted"))
        )
        rejected = sum(1 for s in signals if s.signal_type == "suggestion_feedback" and s.payload_json.get("accepted") is False)
        acceptance_ratio = accepted / max(1, accepted + rejected)

        ratings = [float(f.rating) for f in feedback if f.rating]
        rating_mean = (sum(ratings) / len(ratings)) if ratings else 3.5

        occasions = Counter(
            str((log.context_json or {}).get("occasion", "unknown")).lower()
            for log in outfit_logs
            if isinstance(log.context_json, dict)
        )
        dominant_occasion = occasions.most_common(1)[0][0] if occasions else "casual"
        change_point_score = _estimate_change_point(signals)

        state_factors: list[str] = []
        if role_transition:
            state_factors.append(f"Role transition active: {role_transition}")
        if fit_confidence < 0.45:
            state_factors.append("Lower fit confidence detected; prioritize comfort and context fit.")
        if style_goals:
            state_factors.append(f"Active style goals: {', '.join(style_goals[:3])}")
        if acceptance_ratio < 0.4:
            state_factors.append("Recent low acceptance rate; increase exploration weight.")

        return {
            "life_phase": life_phase,
            "role_transition": role_transition,
            "fit_confidence": round(float(fit_confidence), 3),
            "style_goals": style_goals,
            "acceptance_ratio_90d": round(float(acceptance_ratio), 3),
            "avg_feedback_rating": round(float(rating_mean), 3),
            "dominant_occasion": dominant_occasion,
            "change_point_score": round(change_point_score, 3),
            "state_factors": state_factors,
        }


class PreferenceLearner:
    def update_embeddings(
        self,
        db: Session,
        *,
        user_id: int,
        signals: list[StyleSignalEvent],
        now: datetime,
    ) -> None:
        _refresh_preference_embeddings(db, user_id=user_id, signals=signals, now=now)


def record_style_signal(
    db: Session,
    *,
    user_id: int,
    signal_type: str,
    payload: dict[str, Any],
    source: str,
    weight: float = 0.5,
    occurred_at: datetime | None = None,
) -> StyleSignalEvent:
    model = StyleSignalEvent(
        user_id=user_id,
        signal_type=signal_type,
        payload_json=payload,
        source=source,
        weight=max(0.0, min(1.0, float(weight))),
        occurred_at=occurred_at or datetime.now(UTC),
    )
    db.add(model)
    return model


def create_checkin(db: Session, *, user_id: int, body: ProfileCheckinCreate) -> UserCheckin:
    model = UserCheckin(
        user_id=user_id,
        schema_version=body.schema_version,
        life_phase=body.life_phase,
        role_transition=body.role_transition,
        body_change_note=body.body_change_note,
        fit_confidence=body.fit_confidence,
        style_goals_json=body.style_goals,
        context_weights_json=body.context_weights,
        effective_from=body.effective_from or datetime.now(UTC),
    )
    db.add(model)
    db.flush()
    record_style_signal(
        db,
        user_id=user_id,
        signal_type="checkin",
        source="profile_checkin",
        weight=0.9,
        payload={
            "checkin_id": model.id,
            "life_phase": model.life_phase,
            "role_transition": model.role_transition,
            "fit_confidence": model.fit_confidence,
            "style_goals": model.style_goals_json,
        },
        occurred_at=model.effective_from,
    )
    refresh_temporal_state(db, user_id=user_id)
    db.commit()
    db.refresh(model)
    return model


def get_current_temporal_state(db: Session, *, user_id: int) -> dict[str, Any]:
    row = (
        db.query(UserStateTimeline)
        .filter(UserStateTimeline.user_id == user_id, UserStateTimeline.state_key == "current")
        .order_by(UserStateTimeline.created_at.desc())
        .first()
    )
    if row:
        now_utc = datetime.now(UTC)
        row_created_at = row.created_at
        # SQLite often returns naive datetimes; align tz-awareness before subtraction.
        if row_created_at.tzinfo is None:
            now_for_compare = now_utc.replace(tzinfo=None)
        else:
            now_for_compare = now_utc
        row_age = now_for_compare - row_created_at
        if row_age <= timedelta(hours=6):
            data = dict(row.features_json or {})
            data["confidence"] = row.confidence
            data["updated_at"] = row.created_at
            return data
    return refresh_temporal_state(db, user_id=user_id)


def refresh_temporal_state(db: Session, *, user_id: int) -> dict[str, Any]:
    now = datetime.now(UTC)
    cutoff_90 = now - timedelta(days=90)

    checkins = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user_id)
        .order_by(UserCheckin.effective_from.desc())
        .all()
    )
    signals = (
        db.query(StyleSignalEvent)
        .filter(StyleSignalEvent.user_id == user_id, StyleSignalEvent.occurred_at >= cutoff_90)
        .order_by(StyleSignalEvent.occurred_at.desc())
        .all()
    )
    feedback = (
        db.query(FeedbackEvent)
        .filter(FeedbackEvent.user_id == user_id)
        .order_by(FeedbackEvent.created_at.desc())
        .limit(120)
        .all()
    )
    outfit_logs = (
        db.query(OutfitLog)
        .filter(OutfitLog.user_id == user_id)
        .order_by(OutfitLog.worn_at.desc())
        .limit(120)
        .all()
    )

    builder = FeatureBuilder()
    base_features = builder.build(checkins=checkins, signals=signals, feedback=feedback, outfit_logs=outfit_logs)
    fit_confidence = float(base_features["fit_confidence"])
    acceptance_ratio = float(base_features["acceptance_ratio_90d"])
    dominant_occasion = str(base_features["dominant_occasion"])
    dynamic_weights = _derive_dynamic_weights(
        fit_confidence=fit_confidence,
        acceptance_ratio=acceptance_ratio,
        dominant_occasion=dominant_occasion,
    )
    confidence = max(0.2, min(0.95, 0.45 + (acceptance_ratio * 0.35) + (min(1.0, len(signals) / 80) * 0.2)))

    features = dict(base_features)
    features["dynamic_weights"] = dynamic_weights
    features["offline_metrics"] = _compute_offline_metrics(signals=signals, feedback=feedback)

    timeline_row = UserStateTimeline(
        user_id=user_id,
        state_key="current",
        features_json=features,
        source_signal_ids_json=[s.id for s in signals[:20]],
        confidence=confidence,
        created_at=now,
    )
    db.add(timeline_row)

    PreferenceLearner().update_embeddings(db, user_id=user_id, signals=signals, now=now)
    db.flush()

    out = dict(features)
    out["confidence"] = confidence
    out["updated_at"] = now
    return out


def _refresh_preference_embeddings(db: Session, *, user_id: int, signals: list[StyleSignalEvent], now: datetime) -> None:
    by_window: dict[int, list[StyleSignalEvent]] = {7: [], 30: [], 90: []}
    for signal in signals:
        age_days = max(0.0, (now - signal.occurred_at).total_seconds() / 86400.0)
        for window in by_window:
            if age_days <= window:
                by_window[window].append(signal)

    for window, window_signals in by_window.items():
        embedding = _build_embedding_from_signals(window_signals, half_life_days=max(3, window // 3), now=now)
        existing = (
            db.query(PreferenceEmbedding)
            .filter(PreferenceEmbedding.user_id == user_id, PreferenceEmbedding.window_days == window)
            .order_by(PreferenceEmbedding.updated_at.desc())
            .first()
        )
        if existing:
            existing.embedding_json = embedding
            existing.stability_score = float(embedding.get("stability_score", 0.0))
            existing.updated_at = now
        else:
            db.add(
                PreferenceEmbedding(
                    user_id=user_id,
                    window_days=window,
                    embedding_json=embedding,
                    stability_score=float(embedding.get("stability_score", 0.0)),
                    updated_at=now,
                )
            )


def _build_embedding_from_signals(signals: list[StyleSignalEvent], *, half_life_days: int, now: datetime) -> dict[str, Any]:
    if not signals:
        return {"style_goal_weights": {}, "occasion_weights": {}, "stability_score": 0.0}
    decay_lambda = math.log(2) / max(1.0, float(half_life_days))
    style_weights: Counter[str] = Counter()
    occasion_weights: Counter[str] = Counter()
    volume = 0.0
    for s in signals:
        age_days = max(0.0, (now - s.occurred_at).total_seconds() / 86400.0)
        recency = math.exp(-decay_lambda * age_days)
        base = max(0.0, min(1.0, float(s.weight))) * recency
        payload = s.payload_json or {}
        goals = payload.get("style_goals", [])
        if isinstance(goals, list):
            for goal in goals[:6]:
                style_weights[str(goal).lower()] += base
        occasion = payload.get("occasion")
        if isinstance(occasion, str) and occasion:
            occasion_weights[occasion.lower()] += base
        volume += base
    normalized_style = _normalize_counter(style_weights)
    normalized_occasion = _normalize_counter(occasion_weights)
    diversity = len([k for k, v in normalized_style.items() if v >= 0.1]) + len(
        [k for k, v in normalized_occasion.items() if v >= 0.1]
    )
    stability = max(0.0, min(1.0, 1.0 - min(1.0, diversity / 8.0) + min(0.35, volume / 100.0)))
    return {
        "style_goal_weights": normalized_style,
        "occasion_weights": normalized_occasion,
        "signal_volume": round(volume, 3),
        "stability_score": round(stability, 3),
    }


def _normalize_counter(counter: Counter[str]) -> dict[str, float]:
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {k: round(float(v / total), 4) for k, v in counter.items()}


def _derive_dynamic_weights(*, fit_confidence: float, acceptance_ratio: float, dominant_occasion: str) -> dict[str, float]:
    weights = {"harmony": 0.25, "style_fit": 0.25, "wardrobe_coherence": 0.2, "context_fit": 0.3}
    if fit_confidence < 0.45:
        weights["context_fit"] += 0.08
        weights["style_fit"] -= 0.05
    if acceptance_ratio < 0.4:
        weights["wardrobe_coherence"] += 0.06
        weights["style_fit"] -= 0.03
    if dominant_occasion in {"work", "meeting"}:
        weights["context_fit"] += 0.05
    total = sum(max(0.0, w) for w in weights.values())
    if total <= 0:
        return {"harmony": 0.25, "style_fit": 0.25, "wardrobe_coherence": 0.2, "context_fit": 0.3}
    return {k: round(max(0.0, v) / total, 4) for k, v in weights.items()}


def _estimate_change_point(signals: list[StyleSignalEvent]) -> float:
    if len(signals) < 6:
        return 0.0
    recent = signals[: min(8, len(signals))]
    older = signals[min(8, len(signals)) : min(28, len(signals))]
    if not older:
        return 0.0
    recent_goals = Counter()
    older_goals = Counter()
    for s in recent:
        goals = (s.payload_json or {}).get("style_goals", [])
        if isinstance(goals, list):
            recent_goals.update(str(g).lower() for g in goals)
    for s in older:
        goals = (s.payload_json or {}).get("style_goals", [])
        if isinstance(goals, list):
            older_goals.update(str(g).lower() for g in goals)
    keys = set(recent_goals) | set(older_goals)
    if not keys:
        return 0.0
    diff = sum(abs(recent_goals.get(k, 0) - older_goals.get(k, 0)) for k in keys)
    total = sum(recent_goals.values()) + sum(older_goals.values())
    return max(0.0, min(1.0, diff / max(1, total)))


def _compute_offline_metrics(*, signals: list[StyleSignalEvent], feedback: list[FeedbackEvent]) -> dict[str, float]:
    suggestion_feedback = [s for s in signals if s.signal_type == "suggestion_feedback"]
    accepted = sum(1 for s in suggestion_feedback if bool((s.payload_json or {}).get("accepted")))
    total_feedback = len(suggestion_feedback)
    acceptance_rate = accepted / max(1, total_feedback)
    ratings = [float(f.rating) for f in feedback if f.rating]
    mean_rating = (sum(ratings) / len(ratings)) if ratings else 0.0
    unique_sources = len({s.source for s in signals}) if signals else 0
    novelty_proxy = min(1.0, unique_sources / 6.0)
    stability_proxy = max(0.0, min(1.0, 1.0 - (_estimate_change_point(signals) * 0.6)))
    return {
        "acceptance_rate": round(acceptance_rate, 3),
        "mean_rating": round(mean_rating, 3),
        "novelty_proxy": round(novelty_proxy, 3),
        "stability_proxy": round(stability_proxy, 3),
    }


def parse_item_ids(raw: str) -> list[int]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list):
        return []
    out: list[int] = []
    for item in decoded:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out
