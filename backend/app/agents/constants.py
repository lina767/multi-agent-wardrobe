MOODS = ["power", "creative", "comfort", "social", "focus"]
OCCASIONS = ["casual", "work", "date", "event", "active"]

MOOD_ARCHETYPES: dict[str, dict[str, list[str]]] = {
    "power": {
        "silhouette": ["structured", "tailored"],
        "keywords": ["blazer", "shirt", "trouser", "pointed"],
    },
    "creative": {
        "silhouette": ["mixed-texture", "asymmetric"],
        "keywords": ["statement", "pattern", "layer", "contrast"],
    },
    "comfort": {
        "silhouette": ["relaxed", "soft"],
        "keywords": ["knit", "jersey", "sweat", "earth"],
    },
    "social": {
        "silhouette": ["polished-casual", "trend-forward"],
        "keywords": ["denim", "dress", "jacket", "accent"],
    },
    "focus": {
        "silhouette": ["minimal", "uniform"],
        "keywords": ["neutral", "clean", "simple", "low-contrast"],
    },
}

OCCASION_FORMALITY_TARGET: dict[str, float] = {
    "casual": 0.3,
    "work": 0.7,
    "date": 0.6,
    "event": 0.8,
    "active": 0.2,
}

CATEGORY_SLOT_MAP: dict[str, str] = {
    "top": "top",
    "bottom": "bottom",
    "outer": "outer",
    "shoes": "shoes",
    "accessory": "accessory",
}
