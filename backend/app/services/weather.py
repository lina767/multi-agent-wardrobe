from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import urlopen

from app.config import settings


class WeatherService:
    _CONDITION_BY_CODE: dict[int, str] = {
        1000: "sunny",
        1003: "partly_cloudy",
        1006: "cloudy",
        1009: "cloudy",
        1030: "fog",
        1063: "rain",
        1066: "snow",
        1069: "sleet",
        1072: "sleet",
        1087: "storm",
        1114: "snow",
        1117: "snow",
        1135: "fog",
        1147: "fog",
        1150: "rain",
        1153: "rain",
        1168: "sleet",
        1171: "sleet",
        1180: "rain",
        1183: "rain",
        1186: "rain",
        1189: "rain",
        1192: "rain",
        1195: "rain",
        1198: "sleet",
        1201: "sleet",
        1204: "sleet",
        1207: "sleet",
        1210: "snow",
        1213: "snow",
        1216: "snow",
        1219: "snow",
        1222: "snow",
        1225: "snow",
        1237: "sleet",
        1240: "rain",
        1243: "rain",
        1246: "rain",
        1249: "sleet",
        1252: "sleet",
        1255: "snow",
        1258: "snow",
        1261: "sleet",
        1264: "sleet",
        1273: "storm",
        1276: "storm",
        1279: "snow",
        1282: "snow",
    }

    @classmethod
    def _normalize_condition(cls, condition_text: str | None, condition_code: int | None, is_day: int | None) -> str:
        if condition_code is not None:
            mapped = cls._CONDITION_BY_CODE.get(condition_code)
            if mapped:
                if mapped == "sunny":
                    return "sunny" if is_day == 1 else "clear"
                return mapped
        text = (condition_text or "").strip().lower()
        if not text:
            return "unknown"
        if "thunder" in text or "storm" in text:
            return "storm"
        if "snow" in text or "blizzard" in text:
            return "snow"
        if "sleet" in text or "ice" in text:
            return "sleet"
        if "rain" in text or "drizzle" in text:
            return "rain"
        if "fog" in text or "mist" in text:
            return "fog"
        if "cloud" in text or "overcast" in text:
            return "cloudy"
        if "sun" in text:
            return "sunny"
        if "clear" in text:
            return "clear"
        return "unknown"

    @staticmethod
    def _fallback(location: str) -> dict:
        return {
            "condition": "unknown",
            "condition_raw": None,
            "temperature_c": None,
            "feels_like_c": None,
            "rain_probability": None,
            "uv_index": None,
            "wind_speed_kph": None,
            "forecast_summary": None,
            "location": location,
        }

    async def fetch_current(self, location: str) -> dict:
        if not settings.weather_api_key:
            return self._fallback(location)
        q = quote_plus(location)
        current_url = f"https://api.weatherapi.com/v1/current.json?key={settings.weather_api_key}&q={q}&aqi=no"
        forecast_url = (
            f"https://api.weatherapi.com/v1/forecast.json?key={settings.weather_api_key}"
            f"&q={q}&days=1&aqi=no&alerts=no"
        )
        try:
            with urlopen(current_url, timeout=4) as response:  # nosec B310
                payload = json.loads(response.read().decode("utf-8"))
            current = payload.get("current", {})
            location_payload = payload.get("location", {})
            condition_payload = current.get("condition", {}) if isinstance(current.get("condition"), dict) else {}
            condition_raw = str(condition_payload.get("text", "")).strip() or None
            condition_code = condition_payload.get("code")
            is_day = current.get("is_day")

            rain_probability = None
            forecast_summary = None
            try:
                with urlopen(forecast_url, timeout=4) as response:  # nosec B310
                    forecast_payload = json.loads(response.read().decode("utf-8"))
                forecast_day = ((forecast_payload.get("forecast") or {}).get("forecastday") or [{}])[0]
                day = forecast_day.get("day") if isinstance(forecast_day, dict) else {}
                chance_of_rain = day.get("daily_chance_of_rain")
                chance_of_snow = day.get("daily_chance_of_snow")
                if chance_of_rain is not None:
                    rain_probability = float(chance_of_rain) / 100.0
                if chance_of_snow is not None:
                    snow_probability = float(chance_of_snow) / 100.0
                    rain_probability = max(rain_probability or 0.0, snow_probability)

                day_condition_payload = day.get("condition", {}) if isinstance(day, dict) else {}
                day_text = str(day_condition_payload.get("text", "")).strip()
                forecast_summary = day_text or condition_raw
            except Exception:
                # Keep current weather as source of truth when forecast endpoint fails.
                pass

            precip_mm = current.get("precip_mm")
            if rain_probability is None and precip_mm is not None:
                rain_probability = 1.0 if float(precip_mm) > 0 else 0.0

            return {
                "condition": self._normalize_condition(
                    condition_text=condition_raw,
                    condition_code=int(condition_code) if condition_code is not None else None,
                    is_day=int(is_day) if is_day is not None else None,
                ),
                "condition_raw": condition_raw,
                "temperature_c": current.get("temp_c"),
                "feels_like_c": current.get("feelslike_c"),
                "rain_probability": rain_probability,
                "uv_index": current.get("uv"),
                "wind_speed_kph": current.get("wind_kph"),
                "forecast_summary": forecast_summary,
                "location": location_payload.get("name", location),
            }
        except Exception:
            return self._fallback(location)
