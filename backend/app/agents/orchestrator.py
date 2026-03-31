"""Score merger for recommendation pipeline."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.entities import AgentEvaluationResult
from app.domain.enums import EventType

ALLOWED_WEIGHT_KEYS = ("harmony", "style_fit", "wardrobe_coherence", "context_fit")
ALLOWED_CONFLICT_FLAGS = (
    "weather_mismatch",
    "dresscode_conflict",
    "mood_conflict",
    "palette_conflict",
    "formality_conflict",
    "seasonality_mismatch",
)


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
        candidate_keys = [c["candidate_key"] for c in candidates if isinstance(c.get("candidate_key"), str)]
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
            return self._validate_supervisor_payload(
                payload=payload,
                fallback=fallback,
                default_weights=default_weights,
                candidate_keys=candidate_keys,
            )
        except Exception:
            return fallback

    def _validate_supervisor_payload(
        self,
        *,
        payload: dict[str, Any],
        fallback: dict[str, Any],
        default_weights: dict[str, float],
        candidate_keys: list[str],
    ) -> dict[str, Any]:
        adjusted = payload.get("adjusted_weights", {})
        clean_weights = dict(default_weights)
        if isinstance(adjusted, dict):
            for key in ALLOWED_WEIGHT_KEYS:
                value = adjusted.get(key)
                if isinstance(value, (int, float)):
                    clean_weights[key] = max(0.0, float(value))
        total_w = sum(clean_weights.values())
        if total_w > 0:
            clean_weights = {k: v / total_w for k, v in clean_weights.items()}
        else:
            clean_weights = dict(default_weights)

        ranking_raw = payload.get("final_ranking", [])
        ranking: list[str] = []
        if isinstance(ranking_raw, list):
            for key in ranking_raw:
                if isinstance(key, str) and key in candidate_keys and key not in ranking:
                    ranking.append(key)
        for key in candidate_keys:
            if key not in ranking:
                ranking.append(key)
        if not ranking:
            ranking = list(fallback["final_ranking"])

        synthesis_raw = payload.get("synthesis_text", {})
        synthesis: dict[str, str] = {}
        if isinstance(synthesis_raw, dict):
            for key in candidate_keys:
                text = synthesis_raw.get(key)
                if isinstance(text, str) and text.strip():
                    synthesis[key] = text.strip()
        for key in candidate_keys:
            if key not in synthesis:
                fallback_text = fallback["synthesis_text"].get(key, "")
                synthesis[key] = fallback_text if isinstance(fallback_text, str) else ""

        conflicts_raw = payload.get("conflict_flags", {})
        conflicts: dict[str, list[str]] = {}
        allowed_flags = set(ALLOWED_CONFLICT_FLAGS)
        if isinstance(conflicts_raw, dict):
            for key in candidate_keys:
                raw_list = conflicts_raw.get(key, [])
                if not isinstance(raw_list, list):
                    continue
                deduped: list[str] = []
                for tag in raw_list:
                    if isinstance(tag, str) and tag in allowed_flags and tag not in deduped:
                        deduped.append(tag)
                conflicts[key] = deduped[:3]
        for key in candidate_keys:
            if key not in conflicts:
                conflicts[key] = []

        return {
            "adjusted_weights": {k: round(v, 4) for k, v in clean_weights.items()},
            "final_ranking": ranking,
            "synthesis_text": synthesis,
            "conflict_flags": conflicts,
        }

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
            "Use this exact JSON contract: "
            "{\"adjusted_weights\":{\"harmony\":number,\"style_fit\":number,\"wardrobe_coherence\":number,\"context_fit\":number},"
            "\"final_ranking\":[\"candidate_key\"],"
            "\"synthesis_text\":{\"candidate_key\":\"short explanation\"},"
            "\"conflict_flags\":{\"candidate_key\":[\"weather_mismatch|dresscode_conflict|mood_conflict|palette_conflict|formality_conflict|seasonality_mismatch\"]}}. "
            "Rules: adjusted_weights keys must be exactly harmony/style_fit/wardrobe_coherence/context_fit and sum approximately to 1. "
            "final_ranking must be list of candidate_key strings sorted best-to-worst based on the new weights. "
            "synthesis_text must be an object mapping candidate_key to one concise natural-language explanation. "
            "conflict_flags must use only the allowed enum tags listed in the contract. "
            "Return JSON only, with no markdown and no extra keys."
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
