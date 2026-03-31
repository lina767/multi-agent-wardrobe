from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import urlopen

from app.config import settings


class WeatherService:
    async def fetch_current(self, location: str) -> dict:
        if not settings.openweather_api_key:
            return {"condition": "unknown", "temperature_c": None, "location": location}
        q = quote_plus(location)
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={q}&appid={settings.openweather_api_key}&units=metric"
        )
        try:
            with urlopen(url, timeout=4) as response:  # nosec B310
                payload = json.loads(response.read().decode("utf-8"))
            weather = payload.get("weather", [{}])[0]
            main = payload.get("main", {})
            return {
                "condition": str(weather.get("main", "unknown")),
                "temperature_c": main.get("temp"),
                "location": payload.get("name", location),
            }
        except Exception:
            return {"condition": "unknown", "temperature_c": None, "location": location}
