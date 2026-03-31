"""Score merger for recommendation pipeline."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.entities import AgentEvaluationResult
from app.domain.enums import EventType


class OrchestratorAgent:
    def _default_weights(self, event_type: EventType) -> dict[str, float]:
        return {
            "harmony": 0.25,
            "style_fit": 0.25,
            "wardrobe_coherence": 0.2,
            "context_fit": 0.3 if event_type == EventType.MEETING else 0.2,
        }

    def merge(
        self,
        results: list[AgentEvaluationResult],
        event_type: EventType,
    ) -> tuple[float, dict[str, float], list[str], list[dict[str, Any]], float]:
        partials: dict[str, float] = {}
        reasons: list[str] = []
        trace: list[dict[str, Any]] = []
        for r in results:
            partials.update(r.partial_scores)
            reasons.extend(r.reasons)
            trace.extend(r.trace)

        weights = self._default_weights(event_type)
        if event_type == EventType.MEETING:
            reasons.append("Meeting context gives extra weight to context fit.")

        total_weight = 0.0
        score_sum = 0.0
        for key, weight in weights.items():
            if key in partials:
                score_sum += partials[key] * weight
                total_weight += weight
        total = (score_sum / total_weight) if total_weight > 0 else 0.0

        conf = 0.0
        if partials:
            values = list(partials.values())
            conf = max(values) - min(values)
        partials["orchestrator_confidence"] = round(conf, 4)
        return max(0.0, min(1.0, total)), partials, reasons, trace, conf

    async def supervise(
        self,
        *,
        event_type: EventType,
        context: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        default_weights = self._default_weights(event_type)
        fallback_ranking = [c["candidate_key"] for c in sorted(candidates, key=lambda x: x.get("total_pre_evidence", 0.0), reverse=True)]
        fallback: dict[str, Any] = {
            "adjusted_weights": default_weights,
            "final_ranking": fallback_ranking,
            "synthesis_text": {c["candidate_key"]: c.get("fallback_reason", "") for c in candidates},
            "conflict_flags": {c["candidate_key"]: [] for c in candidates},
        }
        if not settings.anthropic_api_key or not candidates:
            return fallback
        try:
            payload = self._call_haiku_supervisor(default_weights=default_weights, context=context, candidates=candidates)
            adjusted = payload.get("adjusted_weights", {})
            if isinstance(adjusted, dict):
                for k, v in adjusted.items():
                    if k in default_weights and isinstance(v, (int, float)):
                        default_weights[k] = max(0.0, float(v))
                total_w = sum(default_weights.values())
                if total_w > 0:
                    default_weights = {k: v / total_w for k, v in default_weights.items()}
            ranking = payload.get("final_ranking", fallback_ranking)
            if not isinstance(ranking, list) or not ranking:
                ranking = fallback_ranking
            synthesis = payload.get("synthesis_text", fallback["synthesis_text"])
            if not isinstance(synthesis, dict):
                synthesis = fallback["synthesis_text"]
            conflicts = payload.get("conflict_flags", fallback["conflict_flags"])
            if not isinstance(conflicts, dict):
                conflicts = fallback["conflict_flags"]
            return {
                "adjusted_weights": {k: round(v, 4) for k, v in default_weights.items()},
                "final_ranking": ranking,
                "synthesis_text": synthesis,
                "conflict_flags": conflicts,
            }
        except Exception:
            return fallback

    def _call_haiku_supervisor(
        self,
        *,
        default_weights: dict[str, float],
        context: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = (
            "You are a ranking supervisor. Re-weight agent signals based on context, without overriding agent partial scores. "
            "Output strict JSON only with keys: adjusted_weights, final_ranking, synthesis_text, conflict_flags. "
            "Rules: adjusted_weights keys must be harmony/style_fit/wardrobe_coherence/context_fit and sum approximately to 1. "
            "final_ranking must be list of candidate_key strings sorted best-to-worst based on the new weights. "
            "synthesis_text must be an object mapping candidate_key to one concise natural-language explanation. "
            "conflict_flags must be an object mapping candidate_key to list of short conflict strings "
            "(e.g. style high but context weather mismatch)."
        )
        input_payload = {
            "default_weights": default_weights,
            "context": context,
            "candidates": candidates,
        }
        body = {
            "model": settings.agent_reasoning_model,
            "max_tokens": 800,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\nData:\n{json.dumps(input_payload)}",
                }
            ],
        }
        request = Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": settings.anthropic_api_key or "",
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:  # nosec B310
            raw_payload = json.loads(response.read().decode("utf-8"))
        text = raw_payload.get("content", [{}])[0].get("text", "{}").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise
