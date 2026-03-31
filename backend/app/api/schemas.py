"""Pydantic API schemas — versioned under /v1."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ColorFamily,
    DresscodeLevel,
    EventType,
    MoodEnergy,
    WardrobeCategory,
)


# --- Wardrobe ---


class WardrobeItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: WardrobeCategory
    color_families: list[ColorFamily] = Field(default_factory=list)
    formality: DresscodeLevel = DresscodeLevel.CASUAL
    season_tags: list[str] = Field(default_factory=list, description="e.g. spring, winter")
    is_available: bool = True
    style_tags: list[str] = Field(default_factory=list, description="minimalist, classic, etc.")
    brand: str | None = None
    size_label: str | None = None
    material: str | None = None
    quantity: int = Field(1, ge=1)
    purchase_price: float | None = Field(None, ge=0)
    notes: str | None = None


class WardrobeItemCreate(WardrobeItemBase):
    pass


class WardrobeItemUpdate(BaseModel):
    name: str | None = None
    category: WardrobeCategory | None = None
    color_families: list[ColorFamily] | None = None
    formality: DresscodeLevel | None = None
    season_tags: list[str] | None = None
    is_available: bool | None = None
    style_tags: list[str] | None = None
    brand: str | None = None
    size_label: str | None = None
    material: str | None = None
    quantity: int | None = Field(None, ge=1)
    purchase_price: float | None = Field(None, ge=0)
    notes: str | None = None


class WardrobeItemRead(WardrobeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    image_url: str | None = None


# --- Context & recommendation request ---


class ContextInput(BaseModel):
    temperature_c: float | None = Field(None, description="Outdoor temperature Celsius")
    event_type: EventType = EventType.OTHER
    mood: MoodEnergy = MoodEnergy.FOCUS
    dresscode_override: DresscodeLevel | None = None
    notes: str | None = None


class UserStylePreferences(BaseModel):
    preferred_style_tags: list[str] = Field(default_factory=list)
    avoid_style_tags: list[str] = Field(default_factory=list)
    power_outfit_preference: float = Field(
        0.5, ge=0.0, le=1.0, description="Higher = prefer confident/professional silhouette cues"
    )


class RecommendationRequest(BaseModel):
    context: ContextInput
    style_preferences: UserStylePreferences | None = None
    palette_bias: list[ColorFamily] = Field(
        default_factory=list,
        description="User palette / season bias (e.g. warm/cool) for color harmony",
    )
    max_candidates_to_rank: int = Field(50, ge=5, le=500)


# --- Recommendation response ---


class AgentContribution(BaseModel):
    agent: str
    partial_scores: dict[str, float]
    reasons: list[str]


class EvidenceContribution(BaseModel):
    evidence_id: str
    citation_short: str
    effect_on_total: float
    rationale: str


class OutfitSuggestion(BaseModel):
    rank: int
    item_ids: list[int]
    item_names: list[str]
    total_score: float
    agent_contributions: list[AgentContribution]
    evidence_tags: list[EvidenceContribution]
    explanation: str
    decision_trace: list[dict[str, Any]]


class RecommendationResponse(BaseModel):
    suggestions: list[OutfitSuggestion]
    generated_at: datetime
    context_echo: ContextInput


# --- Feedback ---


class FeedbackCreate(BaseModel):
    suggestion_item_ids: list[int]
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    suggestion_item_ids_json: str
    rating: int
    comment: str | None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str = "v1"
