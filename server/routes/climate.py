"""
Climate API endpoints - Temperature and precipitation anomalies.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..db import cache_get, cache_set

router = APIRouter()


class Location(BaseModel):
    latitude: float
    longitude: float


class ClimateAnomaly(BaseModel):
    id: str
    location: Location
    anomaly_type: str  # temperature, precipitation
    value: float  # deviation from normal
    unit: str
    period: str  # e.g., "2024-01"
    severity: str  # low, moderate, high, extreme


class ListClimateAnomaliesResponse(BaseModel):
    anomalies: list[ClimateAnomaly]
    total: int
    updated_at: int


# Open-Meteo API (free, no key required)
OPEN_METEO_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
CLIMATE_CACHE_TTL = 3600  # 1 hour


@router.get("/list-climate-anomalies", response_model=ListClimateAnomaliesResponse)
async def list_climate_anomalies(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    anomaly_type: Optional[str] = Query(None, description="temperature or precipitation"),
    days_back: int = Query(30, ge=1, le=365),
):
    """List climate anomalies from Open-Meteo historical data."""
    cache_key = f"climate:{min_lat}:{max_lat}:{anomaly_type}:{days_back}"

    cached = await cache_get(cache_key)
    if cached:
        return ListClimateAnomaliesResponse(**cached)

    anomalies = []
    now = datetime.utcnow()

    # Sample grid points for climate data
    # In production, would use a proper grid or respond to specific locations
    sample_points = [
        (40.7128, -74.0060, "New York"),
        (51.5074, -0.1278, "London"),
        (35.6762, 139.6503, "Tokyo"),
        (48.8566, 2.3522, "Paris"),
        (-33.8688, 151.2093, "Sydney"),
    ]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for lat, lon, name in sample_points:
                # Check if point is within bounds (if specified)
                if min_lat is not None and lat < min_lat:
                    continue
                if max_lat is not None and lat > max_lat:
                    continue
                if min_lon is not None and lon < min_lon:
                    continue
                if max_lon is not None and lon > max_lon:
                    continue

                start_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
                end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

                response = await client.get(
                    OPEN_METEO_BASE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "start_date": start_date,
                        "end_date": end_date,
                        "daily": "temperature_2m_mean,precipitation_sum",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    daily = data.get("daily", {})
                    temps = daily.get("temperature_2m_mean", [])
                    precip = daily.get("precipitation_sum", [])

                    if temps:
                        avg_temp = sum(t for t in temps if t is not None) / len([t for t in temps if t is not None])
                        # Simple anomaly detection (deviation from assumed normal)
                        # In production, would compare to historical baseline
                        if abs(avg_temp - 15) > 10:  # Simplified threshold
                            severity = "extreme" if abs(avg_temp - 15) > 20 else "high"
                            anomalies.append(ClimateAnomaly(
                                id=f"temp-{lat}-{lon}",
                                location=Location(latitude=lat, longitude=lon),
                                anomaly_type="temperature",
                                value=round(avg_temp - 15, 1),
                                unit="°C",
                                period=f"{start_date} to {end_date}",
                                severity=severity,
                            ))
    except Exception as e:
        print(f"[climate] API error: {e}")

    result = {
        "anomalies": [a.model_dump() for a in anomalies],
        "total": len(anomalies),
        "updated_at": int(now.timestamp() * 1000)
    }

    await cache_set(cache_key, result, CLIMATE_CACHE_TTL)
    return ListClimateAnomaliesResponse(**result)
