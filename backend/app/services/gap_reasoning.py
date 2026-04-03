from __future__ import annotations

import json
from urllib.request import Request, urlopen

from app.config import settings


class GapReasoningService:
    def generate_gap_reason(self, payload: dict) -> str:
        if not settings.anthropic_api_key:
            return self._fallback(payload)
        try:
            return self._call_haiku(payload)
        except Exception:
            return self._fallback(payload)

    def _call_haiku(self, payload: dict) -> str:
        prompt = (
            "Du bist ein Styling-Analyst. Formuliere exakt einen kurzen deutschen Satz "
            "im Stil: 'Dir fehlt ein vielseitiger schwarzer Blazer, der 12 deiner Stuecke aufwerten wuerde.' "
            "Nutze nur Fakten aus den Daten. Keine neuen Zahlen erfinden."
        )
        body = {
            "model": settings.agent_reasoning_model,
            "max_tokens": 90,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\nDaten:\n{json.dumps(payload)}",
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
            result = json.loads(response.read().decode("utf-8"))
        text = result.get("content", [{}])[0].get("text", "").strip()
        return text or self._fallback(payload)

    def _fallback(self, payload: dict) -> str:
        color = payload.get("suggested_color", "neutrale")
        archetype = payload.get("target_item_archetype", "Ergaenzungsteil")
        upgrade_count = int(payload.get("upgrade_count", 0) or 0)
        return (
            f'Dir fehlt ein vielseitiger {color}er {archetype}, '
            f"der {upgrade_count} deiner Stuecke aufwerten wuerde."
        )
