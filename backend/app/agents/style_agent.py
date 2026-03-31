"""Deterministic style profile and mood archetype mapping."""

from __future__ import annotations

from collections import Counter

from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput


class StyleAgent:

    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        pref = {t.lower() for t in pipeline.style_preferences.preferred_style_tags}
        avoid = {t.lower() for t in pipeline.style_preferences.avoid_style_tags}
        ctags = {t.lower() for it in candidate.items for t in it.style_tags}
        hist = {t.lower() for t in pipeline.outfit_history_tags}
        candidate_ids = tuple(sorted(candidate.item_ids))

        score = 0.45
        reasons: list[str] = []
        if pref:
            overlap = len(ctags & pref) / max(len(pref), 1)
            score += overlap * 0.25
            if overlap > 0:
                reasons.append("Matches explicit style preferences.")
        if avoid and ctags & avoid:
            penalty = min(0.2, 0.08 * len(ctags & avoid))
            score -= penalty
            reasons.append("Contains avoided style cues.")
        if hist:
            hist_overlap = len(ctags & hist) / max(len(ctags), 1)
            score += hist_overlap * 0.2
            if hist_overlap > 0:
                reasons.append("Aligned with historically worn style tags.")
        for worn in pipeline.outfit_history:
            worn_ids = tuple(sorted(int(i) for i in worn.get("item_ids", [])))
            if worn_ids != candidate_ids:
                continue
            rating = worn.get("rating")
            if isinstance(rating, int) and rating >= 4:
                score += 0.12
                reasons.append("Positive feedback on this combination boosts confidence.")
            elif isinstance(rating, int) and rating <= 2:
                score -= 0.12
                reasons.append("Negative feedback on this combination lowers confidence.")
            break
        return AgentEvaluationResult(
            agent_name="style",
            partial_scores={"style_fit": max(0.0, min(1.0, score))},
            reasons=reasons or ["Balanced style profile fit."],
        )

    def _weighted_style_counts_from_context(self, outfit_history: list[dict], wardrobe_items: list[dict]) -> Counter[str]:
        counts: Counter[str] = Counter()
        for item in wardrobe_items:
            for tag in item.get("style_tags", []):
                counts[str(tag).lower()] += 1

        # Worn outfits should dominate learned profile (3:1 vs owned-only items).
        for worn in outfit_history:
            tags = [str(t).lower() for t in worn.get("style_tags", [])]
            rating = worn.get("rating")
            weight = 3
            if isinstance(rating, int):
                if rating >= 4:
                    weight = 4
                elif rating <= 2:
                    weight = 1
            for tag in tags:
                counts[tag] += weight
        return counts
