"""Phase-2 placeholder for selfie-based color analysis."""

from app.agents.base import AgentContext, AgentOutput, BaseAgent


class ColorAgent(BaseAgent):
    name = "color_agent"

    async def run(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            payload={
                "color_profile": None,
                "item_color_scores": {},
                "status": "phase_2_pending",
            },
            warnings=["Color analysis not enabled in Phase 1."],
        )
