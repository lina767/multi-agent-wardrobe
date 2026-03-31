from __future__ import annotations

import json
from urllib.request import Request, urlopen

from app.config import settings


class ReasoningService:
    def generate_outfit_why(self, prompt_payload: dict) -> str:
        if not settings.anthropic_api_key:
            return self._fallback(prompt_payload)
        try:
            return self._call_haiku(prompt_payload)
        except Exception:
            return self._fallback(prompt_payload)

    def _call_haiku(self, prompt_payload: dict) -> str:
        prompt = (
            "Write one concise explanation sentence for why this outfit was chosen. "
            "Ground it in decision-fatigue reduction and enclothed cognition mood intent. "
            "Do not mention scores numerically."
        )
        body = {
            "model": settings.agent_reasoning_model,
            "max_tokens": 120,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\nData:\n{json.dumps(prompt_payload)}",
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
        with urlopen(request, timeout=15) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("content", [{}])[0].get("text", "").strip() or self._fallback(prompt_payload)

    def _fallback(self, prompt_payload: dict) -> str:
        return (
            f"Chosen to keep decisions light while matching a {prompt_payload.get('mood', 'focus')} mood and "
            f"{prompt_payload.get('occasion', 'daily')} context with cohesive pieces."
        )
