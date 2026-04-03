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
    SPORT = "sport"
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
    POWER = "power"
    CREATIVE = "creative"
    COMFORT = "comfort"
    SOCIAL = "social"
    FOCUS = "focus"


class ItemStatus(str, Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    DRY_CLEANING = "dry_cleaning"


class FitType(str, Enum):
    OVERSIZED = "oversized"
    REGULAR = "regular"
    SLIM = "slim"
    CROPPED = "cropped"


class WearFrequency(str, Enum):
    RARELY = "rarely"
    SOMETIMES = "sometimes"
    OFTEN = "often"
    VERY_OFTEN = "very_often"


class ItemCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    WORN = "worn"
    NEEDS_REPAIR = "needs_repair"


class MaterialType(str, Enum):
    COTTON = "cotton"
    SILK = "silk"
    WOOL = "wool"
    SYNTHETIC = "synthetic"
    LINEN = "linen"
    JEANS = "jeans"
