from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models import OutfitLog


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, unique=True)
    color_season: Mapped[str | None] = mapped_column(String(32), nullable=True)
    undertone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contrast_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    color_palette: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    selfie_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    primary_style: Mapped[str | None] = mapped_column(String(120), nullable=True)
    secondary_style: Mapped[str | None] = mapped_column(String(120), nullable=True)


class OutfitSuggestion(Base):
    __tablename__ = "outfit_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    color_score: Mapped[float] = mapped_column(Float, default=0.0)
    style_score: Mapped[float] = mapped_column(Float, default=0.0)
    context_score: Mapped[float] = mapped_column(Float, default=0.0)
    mood_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class UserCheckin(Base):
    __tablename__ = "user_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schema_version: Mapped[str] = mapped_column(String(16), default="v1")
    life_phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
    role_transition: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body_change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    style_goals_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    context_weights_json: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class UserStateTimeline(Base):
    __tablename__ = "user_state_timeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    state_key: Mapped[str] = mapped_column(String(64), index=True, default="current")
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_signal_ids_json: Mapped[list[int]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PreferenceEmbedding(Base):
    __tablename__ = "preference_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    window_days: Mapped[int] = mapped_column(Integer, default=30)
    embedding_json: Mapped[dict] = mapped_column(JSON, default=dict)
    stability_score: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class StyleSignalEvent(Base):
    __tablename__ = "style_signal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), default="system")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ColorFeedbackEvent(Base):
    __tablename__ = "color_feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source: Mapped[str] = mapped_column(String(64), default="user")
    predicted_season: Mapped[str] = mapped_column(String(32))
    predicted_undertone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    predicted_contrast_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    predicted_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_season: Mapped[str | None] = mapped_column(String(32), nullable=True)
    corrected_undertone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    corrected_contrast_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
