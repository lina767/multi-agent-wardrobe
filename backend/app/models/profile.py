from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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


class OutfitLog(Base):
    __tablename__ = "outfit_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    occasion: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mood: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weather_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Legacy compatibility columns kept nullable for existing data.
    item_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    worn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
