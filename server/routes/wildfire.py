"""
Wildfire API endpoints - NASA FIRMS satellite fire detection.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..config import settings
from ..db import cache_get, cache_set

router = APIRouter()


class Location(BaseModel):
    latitude: float
    longitude: float


class FireDetection(BaseModel):
    id: str
    location: Location
    brightness: float
    scan: float
    track: float
    satellite: str  # MODIS, VIIRS, etc.
    confidence: str  # low, nominal, high
    frp: float  # Fire Radiative Power
    daynight: str  # D or N
    detected_at: int  # Unix timestamp ms


class ListFireDetectionsResponse(BaseModel):
    fires: list[FireDetection]
    total: int
    updated_at: int


# NASA FIRMS API
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_CACHE_TTL = 600  # 10 minutes


@router.get("/list-fire-detections", response_model=ListFireDetectionsResponse)
async def list_fire_detections(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    days_back: int = Query(1, ge=1, le=10),
    satellite: str = Query("VIIRS_SNPP_NRT", description="Satellite source"),
):
    """List satellite fire detections from NASA FIRMS."""
    # Default to world bounds if not specified
    min_lat = min_lat or -90
    max_lat = max_lat or 90
    min_lon = min_lon or -180
    max_lon = max_lon or 180

    cache_key = f"fires:{min_lat}:{max_lat}:{min_lon}:{max_lon}:{days_back}"

    cached = await cache_get(cache_key)
    if cached:
        return ListFireDetectionsResponse(**cached)

    fires = []
    now = datetime.utcnow()

    if settings.NASA_FIRMS_API_KEY:
        try:
            # FIRMS API format: /api/area/csv/{key}/{source}/{area}/{days}
            # area format: west,south,east,north
            area = f"{min_lon},{min_lat},{max_lon},{max_lat}"
            url = f"{FIRMS_BASE_URL}/{settings.NASA_FIRMS_API_KEY}/{satellite}/{area}/{days_back}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    lines = response.text.strip().split("\n")
                    if len(lines) > 1:
                        headers = lines[0].split(",")

                        # Find column indices
                        lat_idx = headers.index("latitude") if "latitude" in headers else -1
                        lon_idx = headers.index("longitude") if "longitude" in headers else -1
                        bright_idx = headers.index("bright_ti4") if "bright_ti4" in headers else -1
                        conf_idx = headers.index("confidence") if "confidence" in headers else -1
                        frp_idx = headers.index("frp") if "frp" in headers else -1
                        date_idx = headers.index("acq_date") if "acq_date" in headers else -1
                        time_idx = headers.index("acq_time") if "acq_time" in headers else -1
                        daynight_idx = headers.index("daynight") if "daynight" in headers else -1

                        for i, line in enumerate(lines[1:1001]):  # Limit to 1000
                            cols = line.split(",")
                            try:
                                lat = float(cols[lat_idx]) if lat_idx >= 0 else 0
                                lon = float(cols[lon_idx]) if lon_idx >= 0 else 0

                                # Parse datetime
                                acq_date = cols[date_idx] if date_idx >= 0 else "2024-01-01"
                                acq_time = cols[time_idx] if time_idx >= 0 else "0000"
                                dt = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")

                                fires.append(FireDetection(
                                    id=f"fire-{i}-{int(dt.timestamp())}",
                                    location=Location(latitude=lat, longitude=lon),
                                    brightness=float(cols[bright_idx]) if bright_idx >= 0 else 0,
                                    scan=1.0,
                                    track=1.0,
                                    satellite=satellite,
                                    confidence=cols[conf_idx] if conf_idx >= 0 else "nominal",
                                    frp=float(cols[frp_idx]) if frp_idx >= 0 else 0,
                                    daynight=cols[daynight_idx] if daynight_idx >= 0 else "D",
                                    detected_at=int(dt.timestamp() * 1000),
                                ))
                            except (ValueError, IndexError):
                                continue
        except Exception as e:
            print(f"[firms] API error: {e}")

    result = {
        "fires": [f.model_dump() for f in fires],
        "total": len(fires),
        "updated_at": int(now.timestamp() * 1000)
    }

    await cache_set(cache_key, result, FIRMS_CACHE_TTL)
    return ListFireDetectionsResponse(**result)
