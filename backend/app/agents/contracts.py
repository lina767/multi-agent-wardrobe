"""Shared contracts for specialist agent outputs."""

from __future__ import annotations

from typing import Any

from app.domain.entities import AgentEvaluationResult

_DEFAULT_AGENT_SCORES: dict[str, dict[str, float]] = {
    "color": {"harmony": 0.5},
    "style": {"style_fit": 0.5},
    "wardrobe": {"wardrobe_coherence": 0.5},
    "context": {"context_fit": 0.5},
}


def _clamp01(value: Any, fallback: float) -> float:
    if not isinstance(value, (int, float)):
        return fallback
    return max(0.0, min(1.0, float(value)))


def normalize_result_contract(
    result: AgentEvaluationResult,
    *,
    expected_agent: str,
    contract_payload: dict[str, Any] | None = None,
) -> AgentEvaluationResult:
    """Ensure deterministic score keys and attach a machine-readable contract trace."""
    defaults = _DEFAULT_AGENT_SCORES.get(expected_agent, {})
    partial_scores: dict[str, float] = {}
    for key, fallback in defaults.items():
        partial_scores[key] = _clamp01(result.partial_scores.get(key), fallback)
    result.agent_name = expected_agent
    result.partial_scores = partial_scores
    payload = dict(contract_payload or {})
    payload.setdefault("agent", expected_agent)
    result.trace.append({"type": "agent_contract", "schema": "v1", "payload": payload})
    return result
