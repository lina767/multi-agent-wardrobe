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
        if "data/2.5/weather" in url:
            return _MockHTTPResponse(
                {
                    "weather": [{"main": "Clouds"}],
                    "main": {"temp": 12.5, "feels_like": 10.2},
                    "wind": {"speed": 4.0},
                    "rain": {"1h": 0.0},
                    "coord": {"lat": 52.52, "lon": 13.405},
                    "name": "Berlin",
                }
            )
        if "data/2.5/forecast" in url:
            return _MockHTTPResponse(
                {
                    "list": [
                        {"pop": 0.1, "weather": [{"main": "Clouds"}]},
                        {"pop": 0.3, "weather": [{"main": "Rain"}]},
                        {"pop": 0.2, "weather": [{"main": "Clouds"}]},
                    ]
                }
            )
        if "data/3.0/onecall" in url:
            return _MockHTTPResponse({"current": {"uvi": 5.4}})
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("app.services.weather.urlopen", _mock_urlopen)
    result = asyncio.run(WeatherService().fetch_current("Berlin"))
    assert result["condition"] == "Clouds"
    assert result["temperature_c"] == 12.5
    assert result["feels_like_c"] == 10.2
    assert result["rain_probability"] == 0.3
    assert result["uv_index"] == 5.4
    assert result["forecast_summary"] == "Clouds, Rain"
    assert result["wind_speed_kph"] == 14.4


def test_weather_service_returns_fallback_on_exception(monkeypatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "test-key")

    def _raise(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.services.weather.urlopen", _raise)
    result = asyncio.run(WeatherService().fetch_current("Hamburg"))
    assert result["location"] == "Hamburg"
    assert result["condition"] == "unknown"
