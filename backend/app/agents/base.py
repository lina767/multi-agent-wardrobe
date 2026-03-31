from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AgentContext:
    user_id: int
    wardrobe_items: list[dict[str, Any]]
    mood: str
    occasion: str
    location: str | None = None
    weather: dict[str, Any] | None = None
    now: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class AgentOutput:
    agent_name: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentOutput:
        raise NotImplementedError
