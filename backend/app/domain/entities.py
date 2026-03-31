"""Internal dataclasses for agent pipelines (not API-exposed)."""

from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import ColorFamily, DresscodeLevel, EventType, ItemStatus, MoodEnergy, WardrobeCategory
from app.api.schemas import ContextInput, UserStylePreferences


@dataclass
class WardrobeItemDTO:
    id: int
    name: str
    category: WardrobeCategory
    color_families: list[ColorFamily]
    formality: DresscodeLevel
    season_tags: list[str]
    is_available: bool
    status: ItemStatus
    style_tags: list[str]
    brand: str | None = None
    size_label: str | None = None
    material: str | None = None
    quantity: int = 1
    purchase_price: float | None = None
    notes: str | None = None


@dataclass
class OutfitCandidateDTO:
    item_ids: list[int]
    items: list[WardrobeItemDTO]


@dataclass
class AgentEvaluationResult:
    agent_name: str
    partial_scores: dict[str, float]
    reasons: list[str]
    hard_fail: bool = False
    trace: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RecommendationPipelineInput:
    context: ContextInput
    style_preferences: UserStylePreferences
    palette_bias: list[ColorFamily]
    items: list[WardrobeItemDTO]
    outfit_history_tags: list[str] = field(default_factory=list)
    outfit_history: list[dict[str, Any]] = field(default_factory=list)
