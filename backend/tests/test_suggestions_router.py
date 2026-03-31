from app.domain.enums import ColorFamily, EventType
from app.models.profile import UserProfile
from app.routers.suggestions import _occasion_to_event, _palette_bias_from_profile


def test_palette_bias_from_profile_classifies_hex_palette() -> None:
    profile = UserProfile(
        user_id=1,
        color_palette=["#B5B5B5", "#D87A5C", "#4F6DCC", "#A89B77", "#CCE0D1"],
    )
    buckets = _palette_bias_from_profile(profile)
    assert ColorFamily.NEUTRAL in buckets
    assert ColorFamily.WARM in buckets
    assert ColorFamily.COOL in buckets


def test_palette_bias_ignores_invalid_values() -> None:
    profile = UserProfile(user_id=1, color_palette=["not-a-color", "#123", "#GGGGGG"])
    assert _palette_bias_from_profile(profile) == []


def test_occasion_to_event_mapping() -> None:
    assert _occasion_to_event("smart casual") == EventType.MEETING
    assert _occasion_to_event("casual") == EventType.ERRAND
    assert _occasion_to_event("sport") == EventType.ERRAND
    assert _occasion_to_event("unknown-value") == EventType.OTHER
