"""Rule-based supervisor for top-3 outfit suggestions."""

from __future__ import annotations

from itertools import product
from typing import Any

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.agents.constants import CATEGORY_SLOT_MAP, MOOD_ARCHETYPES, OCCASION_FORMALITY_TARGET
from app.services.llm_reasoning import ReasoningService


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    weights = {
        "color_harmony": 0.25,
        "style_match": 0.25,
        "context_fit": 0.25,
        "mood_alignment": 0.15,
        "sustainability": 0.10,
    }
    def __init__(self) -> None:
        self.reasoning = ReasoningService()

    async def run(self, context: AgentContext) -> AgentOutput:
        color_scores = context.shared.get("item_color_scores", {})
        mood_formulas = context.shared.get("mood_formulas", {})
        context_filters = context.shared.get("context_filters", {})
        outfits = self._build_outfits(context.wardrobe_items)[:120]
        ranked = sorted(
            [
                self._score_outfit(items, context, color_scores=color_scores, mood_formulas=mood_formulas, context_filters=context_filters)
                for items in outfits
            ],
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

    def _score_outfit(
        self,
        items: list[dict[str, Any]],
        context: AgentContext,
        *,
        color_scores: dict[int, float],
        mood_formulas: dict[str, list[dict]],
        context_filters: dict[str, Any],
    ) -> dict[str, Any]:
        color = self._score_color(items, color_scores)
        style = self._score_style(items, context.occasion)
        ctx = self._score_context(items, context, context_filters)
        mood = self._score_mood(items, context.mood, mood_formulas)
        sustainability = self._score_sustainability(items)
        conflict_penalty = self._conflict_penalty(items, context, context_filters)
        total = (
            color * self.weights["color_harmony"]
            + style * self.weights["style_match"]
            + ctx * self.weights["context_fit"]
            + mood * self.weights["mood_alignment"]
            + sustainability * self.weights["sustainability"]
        ) - conflict_penalty
        total = max(0.0, min(1.0, total))
        names = ", ".join(i.get("name", "item") for i in items)
        breakdown = {
            "color_score": round(color, 3),
            "style_score": round(style, 3),
            "context_score": round(ctx, 3),
            "mood_alignment": round(mood, 3),
            "sustainability": round(sustainability, 3),
        }
        explanation = self.reasoning.generate_outfit_why(
            {
                "mood": context.mood,
                "occasion": context.occasion,
                "items": [i.get("name", "item") for i in items],
                "breakdown": breakdown,
                "conflict_penalty": round(conflict_penalty, 3),
            }
        )
        return {
            "items": [i["id"] for i in items],
            "item_names": [i.get("name", "item") for i in items],
            "total_score": round(total, 3),
            "reasoning_breakdown": breakdown,
            "explanation": explanation or f"This outfit balances {context.mood} intent with {context.occasion} context: {names}.",
        }

    def _score_color(self, items: list[dict[str, Any]], color_scores: dict[int, float]) -> float:
        if color_scores:
            values = [float(color_scores.get(i["id"], 0.5)) for i in items]
            return min(1.0, max(0.0, sum(values) / max(len(values), 1)))
        tags = [set(i.get("color_families", [])) for i in items]
        overlap = sum(len(left & right) for idx, left in enumerate(tags) for right in tags[idx + 1 :])
        pairs = max((len(tags) * (len(tags) - 1)) / 2, 1)
        return min(0.45 + (overlap / pairs) * 0.25, 1.0)

    def _score_style(self, items: list[dict[str, Any]], occasion: str) -> float:
        target = OCCASION_FORMALITY_TARGET.get(occasion, 0.5)
        formalities = [float(i.get("formality_score", 0.5)) for i in items]
        avg = sum(formalities) / max(len(formalities), 1)
        return max(0.0, 1.0 - abs(avg - target))

    def _score_context(self, items: list[dict[str, Any]], context: AgentContext, context_filters: dict[str, Any]) -> float:
        weather = context_filters.get("weather", context.weather or {})
        temp = weather.get("temperature_c")
        has_outer = any(i.get("category") == "outer" for i in items)
        precipitation = bool(context_filters.get("precipitation", False))
        if temp is not None and temp < 8 and not has_outer:
            return 0.35
        if temp is not None and temp > 24 and has_outer:
            return 0.5
        if precipitation and any("suede" in str(i.get("material", "")).lower() for i in items):
            return 0.45
        return 0.85

    def _score_mood(self, items: list[dict[str, Any]], mood: str, mood_formulas: dict[str, list[dict]]) -> float:
        archetype = MOOD_ARCHETYPES.get(mood.lower(), {})
        keywords = archetype.get("keywords", [])
        text = " ".join(f"{i.get('name', '')} {' '.join(i.get('style_tags', []))}" for i in items).lower()
        matches = sum(1 for kw in keywords if kw in text)
        base = min(0.4 + matches * 0.15, 1.0)
        formulas = mood_formulas.get(mood.lower(), [])
        if not formulas:
            return base
        categories = {i.get("category", "") for i in items}
        bonus = 0.0
        for formula in formulas:
            required = set(formula.get("required_categories", []))
            if required and required.issubset(categories):
                bonus = max(bonus, 0.12)
        return min(1.0, base + bonus)

    def _score_sustainability(self, items: list[dict[str, Any]]) -> float:
        wears = [int(i.get("wear_count", 0)) for i in items]
        if not wears:
            return 0.5
        reused = sum(1 for w in wears if w > 1)
        return min(0.4 + (reused / len(wears)) * 0.6, 1.0)

    def _conflict_penalty(self, items: list[dict[str, Any]], context: AgentContext, context_filters: dict[str, Any]) -> float:
        penalty = 0.0
        precipitation = bool(context_filters.get("precipitation", False))
        if precipitation and any("suede" in str(i.get("material", "")).lower() for i in items):
            penalty += 0.08
        if context.mood == "power" and context.occasion == "casual":
            formal_avg = sum(float(i.get("formality_score", 0.5)) for i in items) / max(len(items), 1)
            if formal_avg > 0.75:
                penalty += 0.05
        return penalty
