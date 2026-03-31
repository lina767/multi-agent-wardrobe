"""Generates outfit candidates from inventory (graph-like combination search)."""

from itertools import product

from app.agents.base import BaseAgent
from app.domain.entities import (
    AgentEvaluationResult,
    OutfitCandidateDTO,
    RecommendationPipelineInput,
    WardrobeItemDTO,
)
from app.domain.enums import WardrobeCategory
from app.domain.scoring import clamp_score, decision_trace_entry


class WardrobeAgent(BaseAgent):
    name = "wardrobe"

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline_input: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        categories = {it.category for it in candidate.items}
        score = 0.68
        reasons: list[str] = []
        if WardrobeCategory.TOP in categories and WardrobeCategory.BOTTOM in categories and WardrobeCategory.SHOES in categories:
            score += 0.12
            reasons.append("Full core outfit (top, bottom, shoes).")
        if WardrobeCategory.OUTER in categories:
            score += 0.05
            reasons.append("Includes layering piece.")
        # Versatility: unique style tag breadth
        tags = {t.lower() for it in candidate.items for t in it.style_tags}
        if len(tags) >= 2:
            score += 0.04
            reasons.append("Multiple style dimensions — higher mixability.")
        trace = [
            decision_trace_entry(self.name, "wardrobe_coherence", round(score, 3), "Inventory graph feasibility."),
        ]
        return AgentEvaluationResult(
            agent_name=self.name,
            partial_scores={"wardrobe_coherence": clamp_score(score)},
            reasons=reasons or ["Baseline wardrobe coherence."],
            trace=trace,
        )

    def build_candidates(
        self,
        items: list[WardrobeItemDTO],
        max_candidates: int = 50,
    ) -> list[OutfitCandidateDTO]:
        available = [i for i in items if i.is_available]
        by_cat: dict[WardrobeCategory, list[WardrobeItemDTO]] = {c: [] for c in WardrobeCategory}
        for it in available:
            if it.category in by_cat:
                by_cat[it.category].append(it)

        tops = by_cat[WardrobeCategory.TOP]
        bottoms = by_cat[WardrobeCategory.BOTTOM]
        shoes = by_cat[WardrobeCategory.SHOES]
        outers = by_cat[WardrobeCategory.OUTER] or [None]
        accs = by_cat[WardrobeCategory.ACCESSORY] or [None]

        if not tops or not bottoms or not shoes:
            return []

        candidates: list[OutfitCandidateDTO] = []
        for top, bottom, shoe, outer, acc in product(tops, bottoms, shoes, outers, accs):
            if max_candidates and len(candidates) >= max_candidates:
                break
            pieces = [top, bottom, shoe]
            if outer is not None:
                pieces.append(outer)
            if acc is not None:
                pieces.append(acc)
            ids = sorted({p.id for p in pieces})
            if len(ids) < 3:
                continue
            candidates.append(OutfitCandidateDTO(item_ids=ids, items=pieces))

        # Dedupe by item id set
        seen: set[tuple[int, ...]] = set()
        unique: list[OutfitCandidateDTO] = []
        for c in candidates:
            key = tuple(sorted(c.item_ids))
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
        return unique[:max_candidates]
