from abc import ABC, abstractmethod

from app.domain.entities import AgentEvaluationResult, OutfitCandidateDTO, RecommendationPipelineInput


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def evaluate(
        self,
        candidate: OutfitCandidateDTO,
        pipeline_input: RecommendationPipelineInput,
    ) -> AgentEvaluationResult:
        pass
