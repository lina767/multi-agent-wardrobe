"""Pydantic API schemas — versioned under /v1."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ColorFamily,
    DresscodeLevel,
    EventType,
    ItemStatus,
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
    weather_tags: list[str] = Field(default_factory=list, description="e.g. cold, rain, wind")
    is_available: bool = True
    status: ItemStatus = ItemStatus.CLEAN
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
    weather_tags: list[str] | None = None
    is_available: bool | None = None
    status: ItemStatus | None = None
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
    condition: str | None = Field(None, description="Normalized weather condition (e.g. sunny, rain, snow)")
    condition_raw: str | None = Field(None, description="Provider-native weather condition label")
    temperature_c: float | None = Field(None, description="Outdoor temperature Celsius")
    feels_like_c: float | None = Field(None, description="Perceived outdoor temperature Celsius")
    rain_probability: float | None = Field(None, ge=0.0, le=1.0, description="Rain probability in range 0..1")
    uv_index: float | None = Field(None, ge=0.0, description="UV index")
    wind_speed_kph: float | None = Field(None, ge=0.0, description="Wind speed in km/h")
    forecast_summary: str | None = Field(None, description="Short upcoming forecast summary")
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


# --- Temporal style intelligence ---


class ProfileCheckinCreate(BaseModel):
    schema_version: str = Field(default="v1", pattern="^v[0-9]+$")
    life_phase: str | None = Field(default=None, max_length=80)
    role_transition: str | None = Field(default=None, max_length=120)
    body_change_note: str | None = None
    fit_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    style_goals: list[str] = Field(default_factory=list, max_length=12)
    context_weights: dict[str, float] | None = None
    effective_from: datetime | None = None


class ProfileCheckinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    schema_version: str
    life_phase: str | None = None
    role_transition: str | None = None
    body_change_note: str | None = None
    fit_confidence: float | None = None
    style_goals_json: list[str]
    context_weights_json: dict[str, float] | None = None
    effective_from: datetime
    created_at: datetime


class TemporalStateRead(BaseModel):
    user_id: int
    state_key: str
    features: dict[str, Any]
    dynamic_weights: dict[str, float]
    state_factors: list[str] = Field(default_factory=list)
    confidence: float
    updated_at: datetime


class ColorProfileFeedbackCreate(BaseModel):
    source: str = Field(default="user", max_length=64)
    predicted_season: str = Field(..., min_length=3, max_length=32)
    predicted_undertone: str | None = Field(default=None, max_length=16)
    predicted_contrast_level: str | None = Field(default=None, max_length=16)
    predicted_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    corrected_season: str | None = Field(default=None, max_length=32)
    corrected_undertone: str | None = Field(default=None, max_length=16)
    corrected_contrast_level: str | None = Field(default=None, max_length=16)
    note: str | None = None


class ColorProfileFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source: str
    predicted_season: str
    predicted_undertone: str | None = None
    predicted_contrast_level: str | None = None
    predicted_confidence: float | None = None
    corrected_season: str | None = None
    corrected_undertone: str | None = None
    corrected_contrast_level: str | None = None
    note: str | None = None
    created_at: datetime


class ProfileRead(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=1, le=120)
    life_phase: str | None = None
    selfie_url: str | None = None
    figure_analysis: str | None = None
    color_profile: dict[str, Any] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=1, le=120)
    life_phase: str | None = Field(default=None, max_length=120)
    figure_analysis: str | None = None


class EmailUpdate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class OnboardingRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=1, le=120)
    life_phase: str | None = Field(default=None, max_length=120)
    figure_analysis: str | None = None
    location: str | None = None


class OnboardingResponse(BaseModel):
    profile: ProfileRead
    temporal_state: TemporalStateRead
    suggestions: list[dict[str, Any]]
