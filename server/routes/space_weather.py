"""
Space Weather API endpoints - Solar activity and geomagnetic conditions.

Data from NOAA Space Weather Prediction Center (SWPC).
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
import httpx

from ..db import cache_get, cache_set

router = APIRouter()


class SolarFlare(BaseModel):
    event_class: Optional[str] = None  # B, C, M, X
    start_time: Optional[str] = None
    peak_time: Optional[str] = None
    end_time: Optional[str] = None


class SpaceWeatherStatus(BaseModel):
    kp_index: float  # 0-9 planetary K-index
    kp_category: str  # quiet, unsettled, active, storm, severe_storm, extreme
    solar_wind_speed: Optional[float] = None  # km/s
    solar_wind_density: Optional[float] = None  # protons/cm3
    latest_flare: Optional[SolarFlare] = None
    geomagnetic_storm_level: str  # G0 (none) through G5 (extreme)
    updated_at: int


# NOAA SWPC endpoints (free, no key required)
KP_INDEX_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"
XRAY_FLARES_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"

SPACE_WEATHER_CACHE_TTL = 900  # 15 minutes


def classify_kp(kp: float) -> tuple[str, str]:
    """Classify Kp index into category and G-scale storm level."""
    if kp < 2:
        return "quiet", "G0"
    elif kp < 4:
        return "unsettled", "G0"
    elif kp < 5:
        return "active", "G0"
    elif kp < 6:
        return "storm", "G1"
    elif kp < 7:
        return "storm", "G2"
    elif kp < 8:
        return "severe_storm", "G3"
    elif kp < 9:
        return "severe_storm", "G4"
    else:
        return "extreme", "G5"


@router.get("/get-space-weather", response_model=SpaceWeatherStatus)
async def get_space_weather():
    """
    Get current space weather conditions including Kp index,
    solar wind parameters, and recent solar flare activity.
    """
    cache_key = "space-weather:current"

    cached = await cache_get(cache_key)
    if cached:
        return SpaceWeatherStatus(**cached)

    kp_index = 2.0
    solar_wind_speed = None
    solar_wind_density = None
    latest_flare = None

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fetch Kp index
        try:
            resp = await client.get(KP_INDEX_URL)
            if resp.status_code == 200:
                data = resp.json()
                # Format: [[time_tag, Kp, ...], ...] — skip header row, get latest
                if len(data) > 1:
                    latest_row = data[-1]
                    kp_index = float(latest_row[1])
        except Exception as e:
            print(f"[space_weather] Kp index fetch error: {e}")

        # Fetch solar wind plasma
        try:
            resp = await client.get(SOLAR_WIND_URL)
            if resp.status_code == 200:
                data = resp.json()
                # Format: [[time_tag, density, speed, temperature], ...] — skip header
                if len(data) > 1:
                    # Find last row with valid data
                    for row in reversed(data[1:]):
                        try:
                            density = float(row[1]) if row[1] else None
                            speed = float(row[2]) if row[2] else None
                            if speed is not None:
                                solar_wind_speed = speed
                                solar_wind_density = density
                                break
                        except (ValueError, IndexError):
                            continue
        except Exception as e:
            print(f"[space_weather] Solar wind fetch error: {e}")

        # Fetch latest X-ray flares
        try:
            resp = await client.get(XRAY_FLARES_URL)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    flare = data[-1]  # Most recent
                    latest_flare = SolarFlare(
                        event_class=flare.get("max_class"),
                        start_time=flare.get("begin_time"),
                        peak_time=flare.get("max_time"),
                        end_time=flare.get("end_time"),
                    )
        except Exception as e:
            print(f"[space_weather] Flare fetch error: {e}")

    kp_category, storm_level = classify_kp(kp_index)
    now = int(datetime.utcnow().timestamp() * 1000)

    result = SpaceWeatherStatus(
        kp_index=round(kp_index, 2),
        kp_category=kp_category,
        solar_wind_speed=round(solar_wind_speed, 1) if solar_wind_speed else None,
        solar_wind_density=round(solar_wind_density, 2) if solar_wind_density else None,
        latest_flare=latest_flare,
        geomagnetic_storm_level=storm_level,
        updated_at=now,
    )

    await cache_set(cache_key, result.model_dump(), SPACE_WEATHER_CACHE_TTL)
    return result
