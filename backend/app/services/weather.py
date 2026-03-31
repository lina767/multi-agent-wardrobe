from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import urlopen

from app.config import settings


class WeatherService:
    @staticmethod
    def _fallback(location: str) -> dict:
        return {
            "condition": "unknown",
            "temperature_c": None,
            "feels_like_c": None,
            "rain_probability": None,
            "uv_index": None,
            "wind_speed_kph": None,
            "forecast_summary": None,
            "location": location,
        }

    async def fetch_current(self, location: str) -> dict:
        if not settings.openweather_api_key:
            return self._fallback(location)
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
            wind = payload.get("wind", {})
            rain = payload.get("rain", {})
            coord = payload.get("coord", {})
            wind_speed_mps = wind.get("speed")
            rain_volume_1h = rain.get("1h") if isinstance(rain, dict) else None

            lat = coord.get("lat")
            lon = coord.get("lon")
            rain_probability = None
            uv_index = None
            forecast_summary = None
            if lat is not None and lon is not None:
                # 5-day forecast endpoint provides precipitation probability (pop).
                forecast_url = (
                    "https://api.openweathermap.org/data/2.5/forecast"
                    f"?lat={lat}&lon={lon}&appid={settings.openweather_api_key}&units=metric"
                )
                with urlopen(forecast_url, timeout=4) as response:  # nosec B310
                    forecast_payload = json.loads(response.read().decode("utf-8"))
                forecast_items = list(forecast_payload.get("list", [])[:4])
                if forecast_items:
                    pop_values = [float(item.get("pop", 0.0) or 0.0) for item in forecast_items]
                    rain_probability = max(pop_values) if pop_values else 0.0
                    parts: list[str] = []
                    for item in forecast_items[:3]:
                        weather_main = str((item.get("weather") or [{}])[0].get("main", "")).strip()
                        if weather_main and weather_main not in parts:
                            parts.append(weather_main)
                    if parts:
                        forecast_summary = ", ".join(parts)

                # UVI from current weather "one call" endpoint.
                uvi_url = (
                    "https://api.openweathermap.org/data/3.0/onecall"
                    f"?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={settings.openweather_api_key}&units=metric"
                )
                with urlopen(uvi_url, timeout=4) as response:  # nosec B310
                    onecall_payload = json.loads(response.read().decode("utf-8"))
                uv_index = onecall_payload.get("current", {}).get("uvi")

            # Fallback rain signal from current rain volume.
            if rain_probability is None and rain_volume_1h is not None:
                rain_probability = 1.0 if float(rain_volume_1h) > 0 else 0.0

            return {
                "condition": str(weather.get("main", "unknown")),
                "temperature_c": main.get("temp"),
                "feels_like_c": main.get("feels_like"),
                "rain_probability": rain_probability,
                "uv_index": uv_index,
                "wind_speed_kph": (float(wind_speed_mps) * 3.6) if wind_speed_mps is not None else None,
                "forecast_summary": forecast_summary,
                "location": payload.get("name", location),
            }
        except Exception:
            return self._fallback(location)
