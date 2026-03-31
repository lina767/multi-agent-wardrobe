"""Rule-based supervisor for top-3 outfit suggestions."""

from __future__ import annotations

from itertools import product
from typing import Any

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.agents.constants import CATEGORY_SLOT_MAP, MOOD_ARCHETYPES, OCCASION_FORMALITY_TARGET


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    weights = {
        "color_harmony": 0.25,
        "style_match": 0.25,
        "context_fit": 0.25,
        "mood_alignment": 0.15,
        "sustainability": 0.10,
    }

    async def run(self, context: AgentContext) -> AgentOutput:
        outfits = self._build_outfits(context.wardrobe_items)[:120]
        ranked = sorted(
            [self._score_outfit(items, context) for items in outfits],
            key=lambda row: row["total_score"],
            reverse=True,
        )[:3]
        return AgentOutput(agent_name=self.name, payload={"suggestions": ranked})

    def _build_outfits(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        by_slot: dict[str, list[dict[str, Any]]] = {"top": [], "bottom": [], "shoes": [], "outer": [], "accessory": []}
        for item in items:
            slot = CATEGORY_SLOT_MAP.get(item.get("category", ""), "")
            if slot in by_slot and item.get("is_available", True):
                by_slot[slot].append(item)
        if not by_slot["top"] or not by_slot["bottom"] or not by_slot["shoes"]:
            return []
        output: list[list[dict[str, Any]]] = []
        for top, bottom, shoes in product(by_slot["top"], by_slot["bottom"], by_slot["shoes"]):
            output.append([top, bottom, shoes])
            for outer in by_slot["outer"][:2]:
                output.append([top, bottom, shoes, outer])
        return output

    def _score_outfit(self, items: list[dict[str, Any]], context: AgentContext) -> dict[str, Any]:
        color = self._score_color(items)
        style = self._score_style(items, context.occasion)
        ctx = self._score_context(items, context)
        mood = self._score_mood(items, context.mood)
        sustainability = self._score_sustainability(items)
        total = (
            color * self.weights["color_harmony"]
            + style * self.weights["style_match"]
            + ctx * self.weights["context_fit"]
            + mood * self.weights["mood_alignment"]
            + sustainability * self.weights["sustainability"]
        )
        names = ", ".join(i.get("name", "item") for i in items)
        return {
            "items": [i["id"] for i in items],
            "item_names": [i.get("name", "item") for i in items],
            "total_score": round(total, 3),
            "reasoning_breakdown": {
                "color_score": round(color, 3),
                "style_score": round(style, 3),
                "context_score": round(ctx, 3),
                "mood_alignment": round(mood, 3),
                "sustainability": round(sustainability, 3),
            },
            "explanation": f"This outfit because it balances {context.mood} intent with {context.occasion} context: {names}.",
        }

    def _score_color(self, items: list[dict[str, Any]]) -> float:
        tags = [set(i.get("color_families", [])) for i in items]
        overlap = 0
        pairs = 0
        for idx, left in enumerate(tags):
            for right in tags[idx + 1 :]:
                pairs += 1
                overlap += len(left & right)
        return min(0.45 + (overlap / max(pairs, 1)) * 0.25, 1.0)

    def _score_style(self, items: list[dict[str, Any]], occasion: str) -> float:
        target = OCCASION_FORMALITY_TARGET.get(occasion, 0.5)
        formalities = [float(i.get("formality_score", 0.5)) for i in items]
        avg = sum(formalities) / max(len(formalities), 1)
        return max(0.0, 1.0 - abs(avg - target))

    def _score_context(self, items: list[dict[str, Any]], context: AgentContext) -> float:
        weather = context.weather or {}
        temp = weather.get("temperature_c")
        has_outer = any(i.get("category") == "outer" for i in items)
        if temp is not None and temp < 8 and not has_outer:
            return 0.35
        if temp is not None and temp > 24 and has_outer:
            return 0.5
        return 0.85

    def _score_mood(self, items: list[dict[str, Any]], mood: str) -> float:
        archetype = MOOD_ARCHETYPES.get(mood.lower(), {})
        keywords = archetype.get("keywords", [])
        text = " ".join(f"{i.get('name', '')} {' '.join(i.get('style_tags', []))}" for i in items).lower()
        matches = sum(1 for kw in keywords if kw in text)
        return min(0.4 + matches * 0.15, 1.0)

    def _score_sustainability(self, items: list[dict[str, Any]]) -> float:
        wears = [int(i.get("wear_count", 0)) for i in items]
        if not wears:
            return 0.5
        reused = sum(1 for w in wears if w > 1)
        return min(0.4 + (reused / len(wears)) * 0.6, 1.0)
