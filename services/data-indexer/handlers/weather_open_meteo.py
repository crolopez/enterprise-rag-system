"""
Weather Open-Meteo Handler

Collects weather data for configured locations using the Open-Meteo API
and keeps forecasts synchronized in Qdrant for RAG context injection.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from base import (
    BaseSourceHandler,
    SourceConfig,
    embed_text,
    hash_id,
    upsert_document,
)

logger = logging.getLogger(__name__)

HANDLER_TYPE = "weather_open_meteo"


class WeatherOpenMeteoHandler(BaseSourceHandler):
    """Collect weather data for configured locations using the Open-Meteo API."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, config: SourceConfig):
        super().__init__(config)
        settings = config.settings or {}
        self.locations = settings.get("locations", [])
        if not self.locations:
            raise ValueError("Weather handler requires at least one location")
        self.timezone = settings.get("timezone", "UTC")
        self.forecast_days = settings.get("forecast_days", 3)

    def run(self) -> None:
        logger.info(
            "Updating weather data for %d locations (source=%s)",
            len(self.locations),
            self.config.id,
        )
        for location in self.locations:
            try:
                snapshot = self._fetch_location_snapshot(location)
                if not snapshot:
                    continue

                document_text = self._build_document_text(location, snapshot)
                vector = embed_text(document_text)
                if not vector:
                    continue

                location_id = location.get("id") or self._slugify(location.get("name", "unknown"))
                point_id = hash_id(self.config.id, location_id, snapshot["timestamp"])
                payload = {
                    "source": self.config.id,
                    "location": location.get("name"),
                    "location_id": location_id,
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "timestamp": snapshot["timestamp"],
                    "current": snapshot["current"],
                    "forecast": snapshot["forecast"],
                    "document_text": document_text,
                    "metadata": {
                        "collection": self.config.collection,
                        "handler": HANDLER_TYPE,
                        "type": "weather",
                    },
                }

                if upsert_document(self.config.collection, point_id, vector, payload):
                    logger.info(
                        "Indexed weather snapshot for %s (%s)",
                        location.get("name"),
                        snapshot["timestamp"],
                    )
            except Exception as exc:
                logger.error(
                    "Failed to index weather data for %s: %s",
                    location.get("name", "unknown"),
                    exc,
                )

    def _fetch_location_snapshot(self, location: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        params = {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,precipitation,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": self.timezone,
            "forecast_days": self.forecast_days,
        }
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Weather API request failed (%s): %s", location.get("name"), exc)
            return None

        payload = resp.json()
        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        weather_text = self._describe_weather(current.get("weather_code"))

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "current": {
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather": weather_text,
            },
            "forecast": {
                "max_temp": self._first_or_none(daily.get("temperature_2m_max")),
                "min_temp": self._first_or_none(daily.get("temperature_2m_min")),
                "precipitation": self._first_or_none(daily.get("precipitation_sum")),
            },
        }

    @staticmethod
    def _first_or_none(values: Optional[List[Any]]) -> Optional[Any]:
        return values[0] if isinstance(values, list) and values else None

    @staticmethod
    def _describe_weather(code: Optional[int]) -> str:
        mapping = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return mapping.get(code, f"Unknown (code: {code})")

    @staticmethod
    def _slugify(name: str) -> str:
        return "".join(c.lower() if c.isalnum() else "-" for c in name or "unknown").strip("-")

    def _build_document_text(self, location: Dict[str, Any], snapshot: Dict[str, Any]) -> str:
        name = location.get("name", "Unknown location")
        current = snapshot["current"]
        forecast = snapshot["forecast"]
        return (
            f"Weather Information for {name}\n\n"
            f"Current Weather Conditions:\n"
            f"- Location: {name}\n"
            f"- Temperature: {current.get('temperature')}°C\n"
            f"- Humidity: {current.get('humidity')}%\n"
            f"- Wind Speed: {current.get('wind_speed')} km/h\n"
            f"- Conditions: {current.get('weather')}\n"
            f"- Last Updated: {snapshot['timestamp']}\n\n"
            f"{self.forecast_days}-Day Forecast:\n"
            f"- Maximum Temperature: {forecast.get('max_temp')}°C\n"
            f"- Minimum Temperature: {forecast.get('min_temp')}°C\n"
            f"- Precipitation: {forecast.get('precipitation')} mm\n\n"
            f"Data Source: Open-Meteo API\n"
            f"Collection: {self.config.collection}\n"
        )


HANDLER_CLASS = WeatherOpenMeteoHandler
