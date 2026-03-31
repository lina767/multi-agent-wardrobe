"""Wardrobe graph analysis and deterministic combinatorics."""

from __future__ import annotations

from collections import defaultdict
from itertools import product

from app.agents.constants import CATEGORY_SLOT_MAP
from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput, WardrobeItemDTO


class WardrobeAgent:
    def analyze_wardrobe(self, items: list[dict], color_profile: dict | None = None) -> dict:
        available_items = [i for i in items if i.get("is_available", True)]
        graph = self._build_graph(available_items)
        outfit_potential = self._calculate_outfit_potential(available_items)
        capsules = self._capsule_suggestions(available_items)
        gaps = self._gap_analysis(available_items, graph["edges"], color_profile or {})
        return {
            "wardrobe_graph": graph,
            "outfit_potential": outfit_potential,
            "capsule_suggestions": capsules,
            "gap_analysis": gaps,
        }

    def run(self, context):  # pragma: no cover - compatibility shim
        items = [i for i in context.wardrobe_items if i.get("is_available", True)]
        graph = self._build_graph(items)
        outfit_potential = self._calculate_outfit_potential(items)
        capsules = self._capsule_suggestions(items)
        gaps = self._gap_analysis(items, graph["edges"], context.shared.get("color_profile", {}))
        return {
            "wardrobe_graph": graph,
            "outfit_potential": outfit_potential,
            "capsule_suggestions": capsules,
            "gap_analysis": gaps,
        }

    def _build_graph(self, items: list[dict]) -> dict:
        nodes = [{"item_id": i["id"], "category": i.get("category", "other")} for i in items]
        edges: list[dict] = []
        for idx, left in enumerate(items):
            for right in items[idx + 1 :]:
                score = self._compatibility(left, right)
                if score >= 0.45:
                    edges.append({"left": left["id"], "right": right["id"], "compatibility": round(score, 3)})
        return {"nodes": nodes, "edges": edges}

    def build_candidates(self, items: list[WardrobeItemDTO], max_candidates: int = 120) -> list[OutfitCandidateDTO]:
        by_slot: dict[str, list[WardrobeItemDTO]] = defaultdict(list)
        for item in items:
            if not item.is_available:
                continue
            by_slot[CATEGORY_SLOT_MAP.get(item.category.value, "other")].append(item)

        tops = by_slot["top"]
        bottoms = by_slot["bottom"]
        shoes = by_slot["shoes"]
        if not tops or not bottoms or not shoes:
            return []

        outers = by_slot["outer"] or [None]
        accessories = by_slot["accessory"] or [None]
        out: list[OutfitCandidateDTO] = []
        for top, bottom, shoe, outer, accessory in product(tops, bottoms, shoes, outers, accessories):
            cand_items = [top, bottom, shoe]
            if outer:
                cand_items.append(outer)
            if accessory:
                cand_items.append(accessory)
            out.append(
                OutfitCandidateDTO(
                    item_ids=[it.id for it in cand_items],
                    items=cand_items,
                )
            )
            if len(out) >= max_candidates:
                break
        return out

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        _pipeline: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        categories = {it.category.value for it in candidate.items}
        base = 0.45
        reasons: list[str] = []
        if {"top", "bottom", "shoes"}.issubset(categories):
            base += 0.35
            reasons.append("Core outfit slots are complete.")
        if "outer" in categories:
            base += 0.08
        if "accessory" in categories:
            base += 0.06
        return AgentEvaluationResult(
            agent_name="wardrobe",
            partial_scores={"wardrobe_coherence": min(1.0, base)},
            reasons=reasons or ["Coherent wardrobe composition."],
        )

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

    def _gap_analysis(self, items: list[dict], edges: list[dict], color_profile: dict | None = None) -> list[dict]:
        degree: dict[int, int] = defaultdict(int)
        for edge in edges:
            degree[edge["left"]] += 1
            degree[edge["right"]] += 1
        by_slot: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            by_slot[CATEGORY_SLOT_MAP.get(item.get("category", ""), "other")].append(item)

        tops = len(by_slot["top"])
        bottoms = len(by_slot["bottom"])
        shoes = len(by_slot["shoes"])
        if not tops or not bottoms or not shoes:
            return [{"suggestion": "Add missing core slot items (top, bottom, shoes).", "estimated_new_outfits": 0, "reason": "Core slots are required before meaningful combination growth."}]

        base_total = self._calculate_outfit_potential(items)
        slot_counts = {
            "top": tops,
            "bottom": bottoms,
            "shoes": shoes,
            "outer": len(by_slot["outer"]),
            "accessory": len(by_slot["accessory"]),
        }
        opportunities = {
            "top": bottoms * shoes * max(1, slot_counts["outer"]) * max(1, slot_counts["accessory"]),
            "bottom": tops * shoes * max(1, slot_counts["outer"]) * max(1, slot_counts["accessory"]),
            "shoes": tops * bottoms * max(1, slot_counts["outer"]) * max(1, slot_counts["accessory"]),
            "outer": tops * bottoms * shoes * max(1, slot_counts["accessory"]),
            "accessory": tops * bottoms * shoes * max(1, slot_counts["outer"]),
        }
        slot_scores = {slot: opportunities[slot] / max(1, slot_counts[slot]) for slot in opportunities}
        target_slot = min(slot_scores, key=slot_scores.get)

        simulated = [*items, {"id": -1, "category": target_slot, "season_tags": [], "style_tags": [], "occasion_tags": [], "is_available": True}]
        new_total = self._calculate_outfit_potential(simulated)
        delta = max(0, new_total - base_total)

        palette = list((color_profile or {}).get("palette") or [])
        palette_color = palette[0] if palette else "a palette-aligned tone"

        sparse = sorted(
            [{"item_id": i["id"], "degree": degree.get(i["id"], 0), "name": i.get("name", "item")} for i in items],
            key=lambda x: x["degree"],
        )[:3]

        low_degree_in_slot = [s["name"] for s in sparse if any(it["id"] == s["item_id"] and CATEGORY_SLOT_MAP.get(it.get("category", ""), "other") == target_slot for it in items)]
        weak_links = ", ".join(low_degree_in_slot[:2]) if low_degree_in_slot else ", ".join(s["name"] for s in sparse[:2])

        return [
            {
                "suggestion": f"Add one {target_slot} in {palette_color}",
                "estimated_new_outfits": delta,
                "reason": f"This slot currently bottlenecks combinations; adding one could unlock about {delta} additional outfits and improve connectivity for low-degree items like {weak_links}.",
            }
        ]
