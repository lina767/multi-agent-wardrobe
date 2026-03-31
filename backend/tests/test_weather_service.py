import asyncio
import json

from app.config import settings
from app.services.weather import WeatherService


class _MockHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_weather_service_returns_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "")
    result = asyncio.run(WeatherService().fetch_current("Berlin"))
    assert result["location"] == "Berlin"
    assert result["temperature_c"] is None
    assert result["condition"] == "unknown"


def test_weather_service_fetch_current_success(monkeypatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "test-key")

    def _mock_urlopen(url: str, timeout: int = 4):
        if "/v1/current.json" in url:
            return _MockHTTPResponse(
                {
                    "location": {"name": "Berlin"},
                    "current": {
                        "temp_c": 12.5,
                        "feelslike_c": 10.2,
                        "uv": 5.4,
                        "wind_kph": 14.4,
                        "precip_mm": 0.0,
                        "is_day": 1,
                        "condition": {"text": "Partly cloudy", "code": 1003},
                    },
                }
            )
        if "/v1/forecast.json" in url:
            return _MockHTTPResponse(
                {
                    "forecast": {
                        "forecastday": [
                            {
                                "day": {
                                    "daily_chance_of_rain": 30,
                                    "daily_chance_of_snow": 0,
                                    "condition": {"text": "Patchy rain possible", "code": 1063},
                                }
                            }
                        ]
                    }
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("app.services.weather.urlopen", _mock_urlopen)
    result = asyncio.run(WeatherService().fetch_current("Berlin"))
    assert result["condition"] == "partly_cloudy"
    assert result["condition_raw"] == "Partly cloudy"
    assert result["temperature_c"] == 12.5
    assert result["feels_like_c"] == 10.2
    assert result["rain_probability"] == 0.3
    assert result["uv_index"] == 5.4
    assert result["forecast_summary"] == "Patchy rain possible"
    assert result["wind_speed_kph"] == 14.4


def test_weather_service_returns_fallback_on_exception(monkeypatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "test-key")

    def _raise(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.services.weather.urlopen", _raise)
    result = asyncio.run(WeatherService().fetch_current("Hamburg"))
    assert result["location"] == "Hamburg"
    assert result["condition"] == "unknown"


def test_weather_service_normalizes_snow_condition(monkeypatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "test-key")

    def _mock_urlopen(url: str, timeout: int = 4):
        if "/v1/current.json" in url:
            return _MockHTTPResponse(
                {
                    "location": {"name": "Munich"},
                    "current": {
                        "temp_c": -1.0,
                        "feelslike_c": -4.0,
                        "uv": 1.0,
                        "wind_kph": 8.0,
                        "precip_mm": 0.8,
                        "is_day": 0,
                        "condition": {"text": "Moderate snow", "code": 1219},
                    },
                }
            )
        if "/v1/forecast.json" in url:
            return _MockHTTPResponse(
                {
                    "forecast": {
                        "forecastday": [
                            {
                                "day": {
                                    "daily_chance_of_rain": 20,
                                    "daily_chance_of_snow": 75,
                                    "condition": {"text": "Moderate snow", "code": 1219},
                                }
                            }
                        ]
                    }
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("app.services.weather.urlopen", _mock_urlopen)
    result = asyncio.run(WeatherService().fetch_current("Munich"))
    assert result["condition"] == "snow"
    assert result["rain_probability"] == 0.75
