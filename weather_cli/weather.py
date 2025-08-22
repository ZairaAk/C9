#!/usr/bin/env python3
import argparse
import json
import sys
import textwrap
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any, List

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def http_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(full_url, headers={"User-Agent": "weather-cli/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def geocode_location(query: str) -> Optional[Dict[str, Any]]:
    params = {"name": query, "count": 1, "language": "en", "format": "json"}
    try:
        data = http_get_json(GEOCODE_URL, params)
        results: List[Dict[str, Any]] = data.get("results") or []
        return results[0] if results else None
    except Exception as exc:
        print(f"Geocoding request failed: {exc}", file=sys.stderr)
        return None


def fetch_current_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
        ],
        "timezone": "auto",
    }
    try:
        return http_get_json(FORECAST_URL, params)
    except Exception as exc:
        print(f"Weather request failed: {exc}", file=sys.stderr)
        return None


def render_output(place: Dict[str, Any], weather: Dict[str, Any]) -> None:
    current = weather.get("current_weather", {})
    hourly = weather.get("hourly", {})

    city = place.get("name")
    admin1 = place.get("admin1")
    country = place.get("country")
    lat = place.get("latitude")
    lon = place.get("longitude")

    title_location = f"{city}{', ' + admin1 if admin1 else ''} {country}"
    print(f"Weather for {title_location}")
    print("-" * (len(title_location) + 12))

    if current:
        print(f"Temperature: {current.get('temperature')} °C")
        print(f"Wind: {current.get('windspeed')} km/h")
        print(f"Direction: {current.get('winddirection')}°")
        print(f"Condition Code: {current.get('weathercode')}")
        print(f"Time: {current.get('time')}")

    def latest(hourly_key: str):
        values = hourly.get(hourly_key)
        if isinstance(values, list) and values:
            return values[-1]
        return None

    rh = latest("relative_humidity_2m")
    feels = latest("apparent_temperature")
    precip = latest("precipitation")

    if rh is not None:
        print(f"Humidity: {rh} %")
    if feels is not None:
        print(f"Feels Like: {feels} °C")
    if precip is not None:
        print(f"Precipitation: {precip} mm")

    footer = textwrap.dedent(
        f"""
        Coordinates: {lat:.4f}, {lon:.4f}
        Source: Open-Meteo (no API key required)
        """
    ).strip()
    print(footer)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple CLI weather app using Open-Meteo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("location", help="City name, e.g., 'London' or 'San Francisco'")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    place = geocode_location(args.location)
    if not place:
        print("Location not found.", file=sys.stderr)
        return 1

    weather = fetch_current_weather(place["latitude"], place["longitude"])  # type: ignore[index]
    if not weather or not weather.get("current_weather"):
        print("Failed to retrieve current weather.", file=sys.stderr)
        return 1

    render_output(place, weather)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
