from __future__ import annotations

import colorsys
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import httpx
try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from app.config import settings
from app.domain.enums import ColorFamily, WardrobeCategory

_CATEGORY_CANDIDATES = ["t-shirt", "shirt", "blouse", "pants", "jeans", "jacket", "coat", "sneakers", "shoes", "bag"]
_COLOR_CANDIDATES = ["black", "white", "gray", "beige", "brown", "blue", "red", "green", "yellow", "pink", "purple"]
_STYLE_CANDIDATES = ["casual", "formal", "business", "minimalist", "sporty", "streetwear", "classic"]
_MATERIAL_CANDIDATES = ["leather", "wool", "cotton", "denim", "linen", "silk", "polyester", "knit"]


@dataclass
class VisionTags:
    category: str | None
    color_families: list[str]
    dominant_colors: list[dict[str, Any]]
    style_tags: list[str]
    material: str | None


class HuggingFaceVisionService:
    def __init__(self) -> None:
        self._base_url = "https://api-inference.huggingface.co/models"

    def is_configured(self) -> bool:
        return bool(settings.hf_api_token)

    async def predict_tags(self, image_bytes: bytes) -> VisionTags:
        category = await self._top_label(image_bytes, _CATEGORY_CANDIDATES)
        colors = await self._labels_above_threshold(image_bytes, _COLOR_CANDIDATES, threshold=0.2, top_k=2)
        dominant_colors = _extract_dominant_colors(image_bytes)
        color_families = _map_color_families(colors)
        if not color_families:
            color_families = _infer_color_families_from_dominant(dominant_colors)
        styles = await self._labels_above_threshold(image_bytes, _STYLE_CANDIDATES, threshold=0.23, top_k=3)
        material = await self._top_label(image_bytes, _MATERIAL_CANDIDATES, threshold=0.22)
        return VisionTags(
            category=_map_category(category),
            color_families=color_families,
            dominant_colors=dominant_colors,
            style_tags=_map_style_tags(styles),
            material=_map_material(material),
        )

    async def remove_background(self, image_bytes: bytes) -> bytes:
        headers = self._headers()
        url = f"{self._base_url}/{settings.hf_rmbg_model}"
        async with httpx.AsyncClient(timeout=settings.hf_timeout_seconds) as client:
            response = await self._retry_post_binary(client, url, headers=headers, content=image_bytes)
        content_type = response.headers.get("content-type", "")
        if "image/" not in content_type and not response.content:
            raise RuntimeError("Hugging Face background removal did not return image content.")
        return response.content

    async def _top_label(
        self,
        image_bytes: bytes,
        labels: list[str],
        threshold: float = 0.25,
    ) -> str | None:
        scores = await self._zero_shot_image_labels(image_bytes, labels)
        if not scores:
            return None
        best = scores[0]
        if float(best.get("score", 0.0)) < threshold:
            return None
        return str(best.get("label", "")).strip().lower() or None

    async def _labels_above_threshold(
        self,
        image_bytes: bytes,
        labels: list[str],
        threshold: float,
        top_k: int,
    ) -> list[str]:
        scores = await self._zero_shot_image_labels(image_bytes, labels)
        out: list[str] = []
        for row in scores:
            score = float(row.get("score", 0.0))
            label = str(row.get("label", "")).strip().lower()
            if score >= threshold and label:
                out.append(label)
            if len(out) >= top_k:
                break
        return out

    async def _zero_shot_image_labels(self, image_bytes: bytes, labels: list[str]) -> list[dict[str, Any]]:
        if not labels:
            return []
        headers = self._headers()
        url = f"{self._base_url}/{settings.hf_tagging_model}"
        payload = {"inputs": image_bytes, "parameters": {"candidate_labels": labels}}
        async with httpx.AsyncClient(timeout=settings.hf_timeout_seconds) as client:
            response = await self._retry_post_json(client, url, headers=headers, payload=payload)
        body = response.json()
        if isinstance(body, dict):
            if "labels" in body and "scores" in body:
                labels_out = [str(x).lower() for x in body.get("labels", [])]
                scores_out = body.get("scores", [])
                return [{"label": l, "score": s} for l, s in zip(labels_out, scores_out, strict=False)]
            return []
        if isinstance(body, list):
            parsed: list[dict[str, Any]] = []
            for entry in body:
                if isinstance(entry, dict) and "label" in entry:
                    parsed.append(entry)
            return parsed
        return []

    def _headers(self) -> dict[str, str]:
        token = settings.hf_api_token
        if not token:
            raise RuntimeError("Missing WARDROBE_HF_API_TOKEN for Hugging Face Inference API.")
        return {"Authorization": f"Bearer {token}"}

    async def _retry_post_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        attempts = max(1, settings.hf_max_retries + 1)
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
        raise RuntimeError(f"Hugging Face tagging request failed: {last_error}") from last_error

    async def _retry_post_binary(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        content: bytes,
    ) -> httpx.Response:
        attempts = max(1, settings.hf_max_retries + 1)
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                response = await client.post(url, headers=headers, content=content)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
        raise RuntimeError(f"Hugging Face background removal request failed: {last_error}") from last_error


def _map_category(label: str | None) -> str | None:
    if not label:
        return None
    if label in {"t-shirt", "shirt", "blouse"}:
        return WardrobeCategory.TOP.value
    if label in {"pants", "jeans"}:
        return WardrobeCategory.BOTTOM.value
    if label in {"jacket", "coat"}:
        return WardrobeCategory.OUTER.value
    if label in {"sneakers", "shoes"}:
        return WardrobeCategory.SHOES.value
    if label == "bag":
        return WardrobeCategory.ACCESSORY.value
    return None


def _map_color_families(labels: list[str]) -> list[str]:
    out: list[str] = []
    warm = {"yellow", "orange", "red"}
    cool = {"blue", "green", "purple"}
    earth = {"brown", "beige"}
    neutral = {"black", "white", "gray"}
    pastel = {"pink", "lavender"}
    for label in labels:
        if label in neutral:
            out.append(ColorFamily.NEUTRAL.value)
        elif label in warm:
            out.append(ColorFamily.WARM.value)
        elif label in cool:
            out.append(ColorFamily.COOL.value)
        elif label in earth:
            out.append(ColorFamily.EARTH.value)
        elif label in pastel:
            out.append(ColorFamily.PASTEL.value)
    seen: set[str] = set()
    deduped: list[str] = []
    for entry in out:
        if entry not in seen:
            deduped.append(entry)
            seen.add(entry)
    return deduped[:2]


def _map_style_tags(labels: list[str]) -> list[str]:
    allowed = {"casual", "formal", "business", "minimalist", "sporty", "streetwear", "classic"}
    return [label for label in labels if label in allowed][:3]


def _map_material(label: str | None) -> str | None:
    if not label:
        return None
    allowed = {"leather", "wool", "cotton", "denim", "linen", "silk", "polyester", "knit"}
    return label if label in allowed else None


def _extract_dominant_colors(image_bytes: bytes, max_colors: int = 3) -> list[dict[str, Any]]:
    if not Image:
        return []
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            rgb = img.convert("RGB").resize((96, 96))
            quantized = rgb.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette()
            counts = quantized.getcolors(maxcolors=96 * 96) or []
    except Exception:
        return []

    if not palette or not counts:
        return []
    total = sum(int(c[0]) for c in counts) or 1
    colors: list[dict[str, Any]] = []
    for count, idx in sorted(counts, key=lambda x: x[0], reverse=True)[:max_colors]:
        base = int(idx) * 3
        if base + 2 >= len(palette):
            continue
        r, g, b = int(palette[base]), int(palette[base + 1]), int(palette[base + 2])
        hue, lightness, saturation = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        temp = "neutral"
        if saturation >= 0.1:
            hue_deg = hue * 360.0
            if hue_deg < 70 or hue_deg >= 290:
                temp = "warm"
            elif 70 <= hue_deg < 250:
                temp = "cool"
        colors.append(
            {
                "hex": f"#{r:02X}{g:02X}{b:02X}",
                "proportion": round(float(count) / float(total), 4),
                "hue": round(hue * 360.0, 2),
                "saturation": round(saturation, 4),
                "lightness": round(lightness, 4),
                "temperature": temp,
            }
        )
    return colors


def _infer_color_families_from_dominant(dominant_colors: list[dict[str, Any]]) -> list[str]:
    scores: dict[str, float] = {
        ColorFamily.NEUTRAL.value: 0.0,
        ColorFamily.WARM.value: 0.0,
        ColorFamily.COOL.value: 0.0,
        ColorFamily.EARTH.value: 0.0,
        ColorFamily.PASTEL.value: 0.0,
    }
    for color in dominant_colors:
        proportion = float(color.get("proportion", 0.0) or 0.0)
        saturation = float(color.get("saturation", 0.0) or 0.0)
        lightness = float(color.get("lightness", 0.0) or 0.0)
        hue = float(color.get("hue", 0.0) or 0.0)
        temp = str(color.get("temperature", "neutral") or "neutral").lower()
        if saturation < 0.12:
            scores[ColorFamily.NEUTRAL.value] += proportion
            continue
        if saturation < 0.35 and lightness < 0.65:
            scores[ColorFamily.EARTH.value] += proportion
        elif lightness > 0.72 and saturation < 0.45:
            scores[ColorFamily.PASTEL.value] += proportion
        if temp == "warm" or hue < 70 or hue >= 290:
            scores[ColorFamily.WARM.value] += proportion
        elif temp == "cool" or (70 <= hue < 250):
            scores[ColorFamily.COOL.value] += proportion
        else:
            scores[ColorFamily.NEUTRAL.value] += proportion * 0.4
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    picked = [name for name, score in ranked if score >= 0.2][:2]
    return picked or [ColorFamily.NEUTRAL.value]
