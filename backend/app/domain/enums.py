from enum import Enum


class WardrobeCategory(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    OUTER = "outer"
    SHOES = "shoes"
    ACCESSORY = "accessory"


class ColorFamily(str, Enum):
    NEUTRAL = "neutral"
    WARM = "warm"
    COOL = "cool"
    BOLD = "bold"
    EARTH = "earth"
    PASTEL = "pastel"


class DresscodeLevel(str, Enum):
    CASUAL = "casual"
    SMART_CASUAL = "smart_casual"
    BUSINESS = "business"
    FORMAL = "formal"


class EventType(str, Enum):
    HOME = "home"
    MEETING = "meeting"
    DATE = "date"
    ERRAND = "errand"
    OTHER = "other"


class MoodEnergy(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
