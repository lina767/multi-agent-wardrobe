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
