"""Phase-2 placeholder for deterministic style profiling."""

from app.agents.base import AgentContext, AgentOutput, BaseAgent


class StyleAgent(BaseAgent):
    name = "style_agent"

    async def run(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            payload={
                "style_profile": {"primary_style": "minimal", "secondary_style": "classic"},
                "mood_formulas": {},
                "status": "phase_2_pending",
            },
            warnings=["Style clustering is scheduled for Phase 2."],
        )
