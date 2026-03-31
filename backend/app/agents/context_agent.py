"""Context aggregation for weather and occasion constraints."""

from __future__ import annotations

from app.agents.base import AgentContext, AgentOutput, BaseAgent
from app.services.weather import WeatherService


class ContextAgent(BaseAgent):
    name = "context_agent"

    def __init__(self) -> None:
        self.weather = WeatherService()

    async def run(self, context: AgentContext) -> AgentOutput:
        weather_data = context.weather or {}
        if context.location and not weather_data:
            weather_data = await self.weather.fetch_current(context.location)
        temp = weather_data.get("temperature_c")
        condition = weather_data.get("condition", "unknown")
        payload = {
            "temperature_range": self._range_for_temperature(temp),
            "precipitation": "rain" in condition.lower() or "drizzle" in condition.lower(),
            "formality_level": self._occasion_to_formality(context.occasion),
            "mood": context.mood,
            "time_of_day": "morning" if context.now.hour < 12 else "afternoon" if context.now.hour < 18 else "evening",
            "weather": weather_data,
        }
        return AgentOutput(agent_name=self.name, payload=payload)

    def _range_for_temperature(self, temp: float | None) -> str:
        if temp is None:
            return "unknown"
        if temp < 8:
            return "cold"
        if temp < 18:
            return "mild"
        return "warm"

    def _occasion_to_formality(self, occasion: str) -> str:
        mapping = {"casual": "low", "work": "medium-high", "date": "medium", "event": "high", "active": "low"}
        return mapping.get(occasion.lower(), "medium")
