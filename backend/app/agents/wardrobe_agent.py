"""Wardrobe graph analysis and deterministic combinatorics."""

from __future__ import annotations

from collections import defaultdict
from itertools import product

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.agents.constants import CATEGORY_SLOT_MAP


class WardrobeAgent(BaseAgent):
    name = "wardrobe_agent"

    async def run(self, context: AgentContext) -> AgentOutput:
        items = [i for i in context.wardrobe_items if i.get("is_available", True)]
        graph = self._build_graph(items)
        outfit_potential = self._calculate_outfit_potential(items)
        capsules = self._capsule_suggestions(items)
        gaps = self._gap_analysis(items, graph["edges"])
        return AgentOutput(
            agent_name=self.name,
            payload={
                "wardrobe_graph": graph,
                "outfit_potential": outfit_potential,
                "capsule_suggestions": capsules,
                "gap_analysis": gaps,
            },
        )

    def _build_graph(self, items: list[dict]) -> dict:
        nodes = [{"item_id": i["id"], "category": i.get("category", "other")} for i in items]
        edges: list[dict] = []
        for idx, left in enumerate(items):
            for right in items[idx + 1 :]:
                score = self._compatibility(left, right)
                if score >= 0.45:
                    edges.append({"left": left["id"], "right": right["id"], "compatibility": round(score, 3)})
        return {"nodes": nodes, "edges": edges}

    def _compatibility(self, left: dict, right: dict) -> float:
        category_bonus = 0.0 if left.get("category") == right.get("category") else 0.2
        season_overlap = len(set(left.get("season_tags", [])) & set(right.get("season_tags", [])))
        style_overlap = len(set(left.get("style_tags", [])) & set(right.get("style_tags", [])))
        occasion_overlap = len(set(left.get("occasion_tags", [])) & set(right.get("occasion_tags", [])))
        base = 0.35 + category_bonus + min(season_overlap * 0.12, 0.24) + min(style_overlap * 0.1, 0.2)
        return min(base + min(occasion_overlap * 0.08, 0.16), 1.0)

    def _calculate_outfit_potential(self, items: list[dict]) -> int:
        by_slot: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            slot = CATEGORY_SLOT_MAP.get(item.get("category", ""), "other")
            by_slot[slot].append(item)
        tops = by_slot["top"]
        bottoms = by_slot["bottom"]
        shoes = by_slot["shoes"]
        outers = by_slot["outer"] or [None]
        accessories = by_slot["accessory"] or [None]
        if not tops or not bottoms or not shoes:
            return 0
        return sum(1 for _ in product(tops, bottoms, shoes, outers, accessories))

    def _capsule_suggestions(self, items: list[dict]) -> list[dict]:
        by_slot: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            by_slot[CATEGORY_SLOT_MAP.get(item.get("category", ""), "other")].append(item)
        return [
            {
                "formula": "2 pants + 3 tops + 1 outer + 1 shoes",
                "status": {
                    "pants": len(by_slot["bottom"]),
                    "tops": len(by_slot["top"]),
                    "outer": len(by_slot["outer"]),
                    "shoes": len(by_slot["shoes"]),
                },
            }
        ]

    def _gap_analysis(self, items: list[dict], edges: list[dict]) -> list[dict]:
        degree: dict[int, int] = defaultdict(int)
        for edge in edges:
            degree[edge["left"]] += 1
            degree[edge["right"]] += 1
        sparse = sorted(
            [{"item_id": i["id"], "degree": degree.get(i["id"], 0), "name": i.get("name", "item")} for i in items],
            key=lambda x: x["degree"],
        )[:3]
        return [
            {
                "suggestion": "Add a versatile neutral blazer",
                "estimated_new_outfits": max(6, len(items) // 2),
                "reason": f"Low-connectivity items found: {', '.join(s['name'] for s in sparse)}",
            }
        ]
