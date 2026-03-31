MOODS = ["power", "creative", "comfort", "social", "focus"]
OCCASIONS = ["casual", "smart casual", "event", "sport"]

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
    "smart casual": 0.65,
    "event": 0.8,
    "sport": 0.2,
}

CATEGORY_SLOT_MAP: dict[str, str] = {
    "top": "top",
    "bottom": "bottom",
    "outer": "outer",
    "shoes": "shoes",
    "accessory": "accessory",
}

SEASON_TYPES = [
    "light_spring",
    "true_spring",
    "deep_spring",
    "light_summer",
    "true_summer",
    "deep_summer",
    "soft_autumn",
    "true_autumn",
    "deep_autumn",
    "cool_winter",
    "true_winter",
    "deep_winter",
]

SEASON_PALETTES: dict[str, list[str]] = {
    "light_spring": ["#F4D8B5", "#F5E7A1", "#BEE3B2", "#A6D9F7", "#F4B3A5"],
    "true_spring": ["#FFB347", "#FFD166", "#8FD694", "#57CC99", "#6EC6FF"],
    "deep_spring": ["#E27D60", "#E8A87C", "#C38D9E", "#41B3A3", "#2A9D8F"],
    "light_summer": ["#C9D7E8", "#DCCCE8", "#B8D8D8", "#F3D1DC", "#EDEAE5"],
    "true_summer": ["#8FA8C9", "#A3BFD9", "#7A8C6E", "#B5727A", "#C7CEDB"],
    "deep_summer": ["#5A6E8C", "#6B7A8F", "#8A6F8D", "#567189", "#3E4E62"],
    "soft_autumn": ["#C2A878", "#BFA58A", "#A68A64", "#8E9B74", "#A67C52"],
    "true_autumn": ["#A66A3F", "#C47F3A", "#8C5E3C", "#6B8E23", "#B08D57"],
    "deep_autumn": ["#5C3A21", "#7A4E2D", "#6B4226", "#3D5A40", "#8B5A2B"],
    "cool_winter": ["#5B6CFF", "#7F8CFF", "#3A86FF", "#9D4EDD", "#C77DFF"],
    "true_winter": ["#1A1A1A", "#2B2D42", "#4361EE", "#F72585", "#4CC9F0"],
    "deep_winter": ["#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#8D99AE"],
}

MOOD_OUTFIT_FORMULAS: dict[str, list[dict[str, list[str]]]] = {
    "power": [
        {"required_categories": ["top", "bottom", "shoes"], "keywords": ["blazer", "tailored", "structured"]},
    ],
    "creative": [
        {"required_categories": ["top", "bottom", "shoes"], "keywords": ["pattern", "texture", "statement"]},
    ],
    "comfort": [
        {"required_categories": ["top", "bottom", "shoes"], "keywords": ["knit", "soft", "relaxed"]},
    ],
    "social": [
        {"required_categories": ["top", "bottom", "shoes"], "keywords": ["polished", "trend", "accent"]},
    ],
    "focus": [
        {"required_categories": ["top", "bottom", "shoes"], "keywords": ["minimal", "neutral", "clean"]},
    ],
}
