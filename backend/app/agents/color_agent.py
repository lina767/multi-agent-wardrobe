"""Selfie color profile + wardrobe item harmony scoring."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.agents.constants import SEASON_PALETTES, SEASON_TYPES
from app.config import settings
from app.services.color_math import delta_e_lab, harmony_from_delta_e, hex_to_rgb, rgb_to_lab

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


class ColorAgent(BaseAgent):
    name = "color_agent"

    async def run(self, context: AgentContext) -> AgentOutput:
        profile = context.shared.get("color_profile")
        if not profile:
            profile = self._fallback_profile()
        scores = {}
        for item in context.wardrobe_items:
            dominant = self._dominant_item_hex(item)
            scores[item["id"]] = self._harmony_score(dominant, profile["palette"])
        return AgentOutput(agent_name=self.name, payload={"color_profile": profile, "item_color_scores": scores})

    async def analyze_selfie(self, selfie_bytes: bytes) -> dict:
        if not settings.anthropic_api_key:
            return self._fallback_profile()
        try:
            return self._call_claude_vision(selfie_bytes)
        except Exception:
            return self._fallback_profile()

    def _call_claude_vision(self, selfie_bytes: bytes) -> dict:
        prompt = (
            "You are a color analyst. Use the 12-season system based on hue undertone (warm/cool), "
            "value contrast (light/deep), and chroma (clear/muted). "
            f"Allowed seasons: {', '.join(SEASON_TYPES)}. "
            "Return strict JSON with keys: season, undertone, contrast_level, palette (5 hex colors)."
        )
        body = {
            "model": settings.agent_color_model,
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(selfie_bytes).decode("utf-8"),
                            },
                        },
                    ],
                }
            ],
        }
        request = Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": settings.anthropic_api_key or "",
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
        text = payload.get("content", [{}])[0].get("text", "{}")
        parsed = json.loads(text)
        season = parsed.get("season", "true_summer")
        return {
            "season": season if season in SEASON_TYPES else "true_summer",
            "undertone": parsed.get("undertone", "cool"),
            "contrast_level": parsed.get("contrast_level", "medium"),
            "palette": parsed.get("palette") or SEASON_PALETTES.get(season, SEASON_PALETTES["true_summer"]),
        }

    def _fallback_profile(self) -> dict:
        return {
            "season": "true_summer",
            "undertone": "cool",
            "contrast_level": "medium",
            "palette": SEASON_PALETTES["true_summer"],
        }

    def _dominant_item_hex(self, item: dict) -> str:
        image_path = item.get("image_path")
        if image_path and Image:
            try:
                path = Path(image_path)
                if path.exists():
                    with Image.open(path) as img:
                        small = img.convert("RGB").resize((1, 1))
                        rgb = small.getpixel((0, 0))
                        return "#{:02X}{:02X}{:02X}".format(*rgb)
            except Exception:
                pass
        mapping = {
            "neutral": "#B5B0A1",
            "warm": "#C47F3A",
            "cool": "#8FA8C9",
            "bold": "#B5727A",
            "earth": "#8B6544",
        }
        families = item.get("color_families", [])
        for family in families:
            if str(family).lower() in mapping:
                return mapping[str(family).lower()]
        return "#B5B0A1"

    def _harmony_score(self, item_hex: str, palette: list[str]) -> float:
        item_lab = rgb_to_lab(hex_to_rgb(item_hex))
        deltas = [delta_e_lab(item_lab, rgb_to_lab(hex_to_rgb(color))) for color in palette]
        best = min(deltas) if deltas else 60.0
        return round(harmony_from_delta_e(best), 3)
