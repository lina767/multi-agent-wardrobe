"""Deterministic style profile and mood archetype mapping."""

from __future__ import annotations

from collections import Counter

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.agents.constants import MOOD_OUTFIT_FORMULAS


class StyleAgent(BaseAgent):
    name = "style_agent"

    async def run(self, context: AgentContext) -> AgentOutput:
        tags: list[str] = []
        for item in context.wardrobe_items:
            tags.extend([str(t).lower() for t in item.get("style_tags", [])])
        top = Counter(tags).most_common(2)
        primary = top[0][0] if top else "minimal"
        secondary = top[1][0] if len(top) > 1 else "classic"
        style_rules = [
            "Prioritize worn combinations over merely owned items.",
            "Reduce cognitive load by ranking only three options.",
            "Maintain mood archetype intent while respecting occasion fit.",
        ]
        return AgentOutput(
            agent_name=self.name,
            payload={
                "style_profile": {
                    "primary_style": primary,
                    "secondary_style": secondary,
                    "style_rules": style_rules,
                },
                "mood_formulas": MOOD_OUTFIT_FORMULAS,
            },
        )
