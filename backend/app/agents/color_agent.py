"""Selfie color profile + wardrobe item harmony scoring."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from app.agents.constants import SEASON_PALETTES, SEASON_TYPES
from app.config import settings
from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput
from app.domain.enums import ColorFamily
from app.services.color_math import delta_e_lab, harmony_from_delta_e, hex_to_rgb, rgb_to_lab

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


class ColorAgent:
    def __init__(self) -> None:
        self._backend = self._resolve_backend(settings.color_agent_backend)

    @staticmethod
    def _resolve_backend(name: str) -> str:
        backend = (name or "anthropic_vision").strip().lower()
        if backend in {"fine_tuned", "anthropic_vision", "heuristic"}:
            return backend
        return "anthropic_vision"

    def _normalize_profile(self, profile: dict[str, Any], backend: str) -> dict[str, Any]:
        season = str(profile.get("season") or "true_summer")
        if season not in SEASON_TYPES:
            season = "true_summer"
        palette = profile.get("palette")
        if not isinstance(palette, list):
            palette = []
        clean_palette = [str(c).upper() for c in palette if isinstance(c, str) and c.startswith("#")][:5]
        if not clean_palette:
            clean_palette = list(SEASON_PALETTES.get(season, SEASON_PALETTES["true_summer"]))
        confidence_raw = profile.get("confidence")
        confidence = 0.6 if not isinstance(confidence_raw, (int, float)) else max(0.0, min(1.0, float(confidence_raw)))
        return {
            "season": season,
            "undertone": str(profile.get("undertone") or "cool"),
            "contrast_level": str(profile.get("contrast_level") or "medium"),
            "palette": clean_palette,
            "confidence": round(confidence, 3),
            "backend": backend,
        }

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        palette_bias = set(pipeline.palette_bias)
        item_colors = [cf for it in candidate.items for cf in it.color_families]
        if not item_colors:
            return AgentEvaluationResult(agent_name="color", partial_scores={"harmony": 0.5}, reasons=["No color signals available."])

        neutrals = sum(1 for c in item_colors if c == ColorFamily.NEUTRAL)
        harmony = 0.45 + min(0.3, neutrals * 0.08)
        reasons = ["Neutral anchor improves harmony."]
        if palette_bias:
            overlap = sum(1 for c in item_colors if c in palette_bias)
            harmony += min(0.25, overlap * 0.08)
            if overlap > 0:
                reasons.append("Respects user palette bias.")
        return AgentEvaluationResult(
            agent_name="color",
            partial_scores={"harmony": max(0.0, min(1.0, harmony))},
            reasons=reasons,
        )

    async def analyze_selfie(self, selfie_bytes: bytes) -> dict:
        profile = self._fallback_profile()
        try:
            if self._backend == "fine_tuned":
                profile = self._call_fine_tuned_vision(selfie_bytes)
            elif self._backend == "heuristic":
                profile = self._heuristic_profile(selfie_bytes)
            else:
                profile = self._call_claude_vision(selfie_bytes)
        except Exception:
            profile = self._fallback_profile()

        profile = self._normalize_profile(profile, self._backend)
        if profile["confidence"] < settings.color_profile_min_confidence:
            fallback = self._normalize_profile(self._fallback_profile(), "heuristic")
            fallback["used_fallback"] = True
            fallback["fallback_reason"] = "low_confidence"
            fallback["primary_backend"] = profile["backend"]
            return fallback

        if settings.color_agent_shadow_mode:
            profile["shadow"] = self._run_shadow_profile(selfie_bytes, primary_backend=profile["backend"])
        return profile

    def _call_claude_vision(self, selfie_bytes: bytes) -> dict:
        if not settings.anthropic_api_key:
            return self._fallback_profile()
        prompt = (
            "You are a color analyst. Use the 12-season system based on hue undertone (warm/cool), "
            "value contrast (light/deep), and chroma (clear/muted). "
            f"Allowed seasons: {', '.join(SEASON_TYPES)}. "
            "Return strict JSON with keys: season, undertone, contrast_level, palette (5 hex colors), confidence (0..1)."
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
            "confidence": parsed.get("confidence", 0.72),
        }

    def _fallback_profile(self) -> dict:
        return {
            "season": "true_summer",
            "undertone": "cool",
            "contrast_level": "medium",
            "palette": SEASON_PALETTES["true_summer"],
            "confidence": 0.58,
        }

    def _heuristic_profile(self, selfie_bytes: bytes) -> dict:
        dominant = self._dominant_hex_from_bytes(selfie_bytes) or "#A1A6B8"
        r = int(dominant[1:3], 16)
        b = int(dominant[5:7], 16)
        cool_hint = b >= r
        season = "true_summer" if cool_hint else "soft_autumn"
        return {
            "season": season,
            "undertone": "cool" if cool_hint else "warm",
            "contrast_level": "medium",
            "palette": SEASON_PALETTES.get(season, SEASON_PALETTES["true_summer"]),
            "confidence": 0.62,
        }

    def _call_fine_tuned_vision(self, selfie_bytes: bytes) -> dict:
        endpoint = settings.color_fine_tuned_endpoint
        if not endpoint:
            return self._heuristic_profile(selfie_bytes)
        body = {"image_b64": base64.b64encode(selfie_bytes).decode("utf-8")}
        request = Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Invalid fine-tuned payload")
        return payload

    def _run_shadow_profile(self, selfie_bytes: bytes, primary_backend: str) -> dict[str, Any]:
        shadow_backend = "anthropic_vision" if primary_backend != "anthropic_vision" else "heuristic"
        try:
            if shadow_backend == "anthropic_vision":
                shadow = self._normalize_profile(self._call_claude_vision(selfie_bytes), shadow_backend)
            else:
                shadow = self._normalize_profile(self._heuristic_profile(selfie_bytes), shadow_backend)
            return {"backend": shadow_backend, "season": shadow["season"], "confidence": shadow["confidence"]}
        except Exception:
            return {"backend": shadow_backend, "status": "failed"}

    def _dominant_hex_from_bytes(self, image_bytes: bytes) -> str | None:
        if not Image:
            return None
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                return self._dominant_hex_from_clusters(img)
        except Exception:
            return None

    def _dominant_item_hex(self, item: dict) -> str:
        image_path = item.get("image_path")
        if image_path and Image:
            try:
                if str(image_path).startswith(("http://", "https://")):
                    with urlopen(image_path, timeout=10) as response:  # nosec B310
                        raw = response.read()
                    with Image.open(BytesIO(raw)) as img:
                        return self._dominant_hex_from_clusters(img)
                path = Path(image_path)
                if path.exists():
                    with Image.open(path) as img:
                        return self._dominant_hex_from_clusters(img)
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

    def _dominant_hex_from_clusters(self, img: "Image.Image") -> str:
        rgb = img.convert("RGB")
        pixels = list(rgb.resize((120, 120)).getdata())
        if not pixels:
            return "#B5B0A1"
        centroids = [pixels[0], pixels[len(pixels) // 2], pixels[-1]]
        clusters: list[list[tuple[int, int, int]]] = [[], [], []]
        for _ in range(6):
            clusters = [[], [], []]
            for p in pixels:
                idx = min(range(3), key=lambda i: (p[0] - centroids[i][0]) ** 2 + (p[1] - centroids[i][1]) ** 2 + (p[2] - centroids[i][2]) ** 2)
                clusters[idx].append(p)
            updated: list[tuple[int, int, int]] = []
            for i, cluster in enumerate(clusters):
                if not cluster:
                    updated.append(centroids[i])
                    continue
                r = int(sum(px[0] for px in cluster) / len(cluster))
                g = int(sum(px[1] for px in cluster) / len(cluster))
                b = int(sum(px[2] for px in cluster) / len(cluster))
                updated.append((r, g, b))
            centroids = updated
        idx = max(range(3), key=lambda i: len(clusters[i]))
        r, g, b = centroids[idx]
        return "#{:02X}{:02X}{:02X}".format(r, g, b)

    def _harmony_score(self, item_hex: str, palette: list[str]) -> float:
        item_lab = rgb_to_lab(hex_to_rgb(item_hex))
        deltas = [delta_e_lab(item_lab, rgb_to_lab(hex_to_rgb(color))) for color in palette]
        best = min(deltas) if deltas else 60.0
        return round(harmony_from_delta_e(best), 3)
