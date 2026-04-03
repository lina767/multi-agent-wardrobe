"""Anthropic vision fallback for wardrobe item tagging when Hugging Face is unavailable."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.domain.enums import ColorFamily, WardrobeCategory
from app.services.hf_vision_service import (
    VisionTags,
    _extract_dominant_colors,
    _infer_color_families_from_dominant,
    _map_material,
    _map_style_tags,
)

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {c.value for c in WardrobeCategory}
_VALID_COLOR_FAMILIES = {c.value for c in ColorFamily}


def _media_type_for_extension(ext: str) -> str:
    e = ext.lower().lstrip(".")
    if e in {"jpg", "jpeg"}:
        return "image/jpeg"
    if e == "png":
        return "image/png"
    if e == "webp":
        return "image/webp"
    if e == "gif":
        return "image/gif"
    return "image/jpeg"


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _parse_claude_json(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(text)
    parsed = json.loads(cleaned)
    return parsed if isinstance(parsed, dict) else {}


def _dominant_from_hex(hex_str: str | None, image_bytes: bytes) -> list[dict[str, Any]]:
    dominant = _extract_dominant_colors(image_bytes)
    if not hex_str or not isinstance(hex_str, str):
        return dominant
    h = hex_str.strip()
    if not re.match(r"^#[0-9A-Fa-f]{6}$", h):
        return dominant
    if dominant:
        return dominant
    return [
        {
            "hex": h.upper(),
            "proportion": 1.0,
            "hue": 0.0,
            "saturation": 0.0,
            "lightness": 0.0,
            "temperature": "neutral",
        }
    ]


def vision_tags_from_claude_payload(parsed: dict[str, Any], image_bytes: bytes) -> VisionTags:
    cat = parsed.get("category")
    category = cat if isinstance(cat, str) and cat in _VALID_CATEGORIES else None

    raw_families = parsed.get("color_families")
    color_families: list[str] = []
    if isinstance(raw_families, list):
        for x in raw_families:
            if isinstance(x, str) and x in _VALID_COLOR_FAMILIES and x not in color_families:
                color_families.append(x)
            if len(color_families) >= 2:
                break

    dominant_colors = _dominant_from_hex(parsed.get("dominant_hex"), image_bytes)
    if not color_families:
        color_families = _infer_color_families_from_dominant(dominant_colors)

    raw_styles = parsed.get("style_tags")
    style_labels: list[str] = []
    if isinstance(raw_styles, list):
        style_labels = [str(s).strip().lower() for s in raw_styles if s][:3]
    elif isinstance(raw_styles, str) and raw_styles.strip():
        style_labels = [raw_styles.strip().lower()]

    raw_material = parsed.get("material")
    material = _map_material(str(raw_material).strip().lower()) if raw_material else None

    return VisionTags(
        category=category,
        color_families=color_families,
        dominant_colors=dominant_colors,
        style_tags=_map_style_tags(style_labels),
        material=material,
    )


async def predict_wardrobe_tags_anthropic(image_bytes: bytes, extension: str) -> VisionTags:
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key not configured for wardrobe vision fallback.")

    media_type = _media_type_for_extension(extension)
    prompt = (
        "You analyze a single clothing/garment photo for a digital wardrobe. "
        "Return ONLY valid JSON (no markdown) with exactly these keys:\n"
        "- category: one of top, bottom, outer, shoes, accessory\n"
        "- color_families: array of 1-2 values from neutral, warm, cool, bold, earth, pastel "
        "(wardrobe color groups, not raw color names)\n"
        "- dominant_hex: optional string like #A1B2C3 for the main visible garment color\n"
        "- style_tags: 0-3 from casual, formal, business, minimalist, sporty, streetwear, classic\n"
        "- material: one of leather, wool, cotton, jeans, linen, silk, polyester, knit or null (use jeans for denim)\n"
        "Focus on the main garment. Be decisive."
    )
    body = {
        # For wardrobe tagging fallback prefer the lightweight reasoning model (typically Haiku).
        "model": settings.agent_reasoning_model,
        "max_tokens": 400,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        },
                    },
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "content-type": "application/json",
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            json=body,
        )
        response.raise_for_status()
        payload = response.json()

    text_parts: list[str] = []
    for block in payload.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text", "")))
    raw_text = "".join(text_parts).strip()
    if not raw_text:
        raise RuntimeError("Empty response from Claude vision.")

    try:
        parsed = _parse_claude_json(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("claude_wardrobe_json_parse_failed", extra={"snippet": raw_text[:200]})
        raise RuntimeError("Claude vision returned non-JSON.") from exc

    return vision_tags_from_claude_payload(parsed, image_bytes)
