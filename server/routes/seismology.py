"""
Seismology API endpoints - USGS earthquake data.
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
    depth: float  # km


class Earthquake(BaseModel):
    id: str
    magnitude: float
    place: str
    location: Location
    occurred_at: int  # Unix timestamp ms
    tsunami_warning: bool = False
    felt_reports: int = 0
    alert_level: Optional[str] = None  # green, yellow, orange, red
    url: str


class ListEarthquakesResponse(BaseModel):
    earthquakes: list[Earthquake]
    total: int


# USGS API configuration
USGS_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_CACHE_TTL = 300  # 5 minutes for real-time data


@router.get("/list-earthquakes", response_model=ListEarthquakesResponse)
async def list_earthquakes(
    start: Optional[int] = Query(None, description="Start timestamp (ms)"),
    end: Optional[int] = Query(None, description="End timestamp (ms)"),
    min_magnitude: float = Query(4.0, ge=0, le=10, description="Minimum magnitude"),
    max_magnitude: Optional[float] = Query(None, ge=0, le=10, description="Maximum magnitude"),
    min_latitude: Optional[float] = Query(None, ge=-90, le=90),
    max_latitude: Optional[float] = Query(None, ge=-90, le=90),
    min_longitude: Optional[float] = Query(None, ge=-180, le=180),
    max_longitude: Optional[float] = Query(None, ge=-180, le=180),
    limit: int = Query(500, le=2000),
):
    """List earthquakes from USGS within time and magnitude range."""
    # Build cache key from parameters
    cache_key = f"usgs:{min_magnitude}:{start}:{end}:{min_latitude}:{max_latitude}"

    cached = await cache_get(cache_key)
    if cached:
        return ListEarthquakesResponse(**cached)

    # Calculate date range (default: last 7 days)
    now = datetime.utcnow()
    start_time = datetime.fromtimestamp(start / 1000) if start else now - timedelta(days=7)
    end_time = datetime.fromtimestamp(end / 1000) if end else now

    earthquakes = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "format": "geojson",
                "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": min_magnitude,
                "limit": limit,
                "orderby": "time",
            }
            if max_magnitude:
                params["maxmagnitude"] = max_magnitude
            if min_latitude is not None:
                params["minlatitude"] = min_latitude
            if max_latitude is not None:
                params["maxlatitude"] = max_latitude
            if min_longitude is not None:
                params["minlongitude"] = min_longitude
            if max_longitude is not None:
                params["maxlongitude"] = max_longitude

            response = await client.get(USGS_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            for feature in data.get("features", []):
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])

                if len(coords) >= 3:
                    earthquakes.append(Earthquake(
                        id=feature.get("id", ""),
                        magnitude=float(props.get("mag", 0) or 0),
                        place=props.get("place", "Unknown location"),
                        location=Location(
                            latitude=float(coords[1]),
                            longitude=float(coords[0]),
                            depth=float(coords[2]),
                        ),
                        occurred_at=int(props.get("time", 0)),
                        tsunami_warning=bool(props.get("tsunami", 0)),
                        felt_reports=int(props.get("felt", 0) or 0),
                        alert_level=props.get("alert"),
                        url=props.get("url", ""),
                    ))
    except Exception as e:
        print(f"[usgs] API error: {e}")

    result = {
        "earthquakes": [eq.model_dump() for eq in earthquakes],
        "total": len(earthquakes)
    }
    await cache_set(cache_key, result, USGS_CACHE_TTL)
    return ListEarthquakesResponse(**result)


@router.get("/significant-earthquakes", response_model=ListEarthquakesResponse)
async def list_significant_earthquakes(
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
):
    """List significant earthquakes (M6.0+) from the past N days."""
    cache_key = f"usgs:significant:{days}"

    cached = await cache_get(cache_key)
    if cached:
        return ListEarthquakesResponse(**cached)

    now = datetime.utcnow()
    start_time = now - timedelta(days=days)

    earthquakes = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "format": "geojson",
                "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": 6.0,
                "orderby": "magnitude",
            }

            response = await client.get(USGS_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            for feature in data.get("features", []):
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])

                if len(coords) >= 3:
                    earthquakes.append(Earthquake(
                        id=feature.get("id", ""),
                        magnitude=float(props.get("mag", 0) or 0),
                        place=props.get("place", "Unknown location"),
                        location=Location(
                            latitude=float(coords[1]),
                            longitude=float(coords[0]),
                            depth=float(coords[2]),
                        ),
                        occurred_at=int(props.get("time", 0)),
                        tsunami_warning=bool(props.get("tsunami", 0)),
                        felt_reports=int(props.get("felt", 0) or 0),
                        alert_level=props.get("alert"),
                        url=props.get("url", ""),
                    ))
    except Exception as e:
        print(f"[usgs] API error: {e}")

    result = {
        "earthquakes": [eq.model_dump() for eq in earthquakes],
        "total": len(earthquakes)
    }
    await cache_set(cache_key, result, USGS_CACHE_TTL)
    return ListEarthquakesResponse(**result)
