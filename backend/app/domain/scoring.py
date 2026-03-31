"""Shared scoring utilities for agents and orchestrator."""

from typing import Any

MIN_SCORE = 0.0
MAX_SCORE = 1.0


def clamp_score(value: float) -> float:
    return max(MIN_SCORE, min(MAX_SCORE, value))


def merge_partial_scores(weights: dict[str, float], partials: dict[str, float]) -> float:
    """Weighted sum, normalized by weight sum."""
    total_w = sum(weights.values()) or 1.0
    acc = 0.0
    for key, w in weights.items():
        acc += w * partials.get(key, 0.0)
    return clamp_score(acc / total_w)


def decision_trace_entry(
    agent: str,
    field: str,
    value: Any,
    rationale: str,
) -> dict[str, Any]:
    return {"agent": agent, "field": field, "value": value, "rationale": rationale}
