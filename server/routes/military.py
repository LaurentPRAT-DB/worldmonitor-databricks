"""
Military API endpoints - Flight tracking, bases, fleet reports.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import cache_get, cache_set

router = APIRouter()


class Position(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = None


class MilitaryFlight(BaseModel):
    icao24: str
    callsign: Optional[str] = None
    origin_country: str
    position: Position
    velocity: float = 0
    heading: float = 0
    vertical_rate: float = 0
    on_ground: bool = False
    classification: str = "unknown"  # military, government, unknown
    timestamp: int


class ListMilitaryFlightsResponse(BaseModel):
    flights: list[MilitaryFlight]
    total: int
    updated_at: int


class MilitaryBase(BaseModel):
    id: str
    name: str
    country: str
    position: Position
    base_type: str  # air, naval, army, joint
    operator: Optional[str] = None


class ListMilitaryBasesResponse(BaseModel):
    bases: list[MilitaryBase]
    total: int


class TheaterPosture(BaseModel):
    theater: str
    alert_level: str  # low, elevated, high, critical
    active_flights: int
    recent_incidents: int
    assessment: str


@router.get("/list-military-flights", response_model=ListMilitaryFlightsResponse)
async def list_military_flights(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
):
    """List military/government aircraft from OpenSky Network."""
    cache_key = f"flights:military:{min_lat}:{max_lat}:{min_lon}:{max_lon}"

    cached = await cache_get(cache_key)
    if cached:
        return ListMilitaryFlightsResponse(**cached)

    # Demo mode - OpenSky integration would go here
    now = int(datetime.utcnow().timestamp() * 1000)
    result = {
        "flights": [],
        "total": 0,
        "updated_at": now
    }

    await cache_set(cache_key, result, 60)  # 1 minute cache
    return ListMilitaryFlightsResponse(**result)


@router.get("/list-military-bases", response_model=ListMilitaryBasesResponse)
async def list_military_bases(
    country: Optional[str] = Query(None, description="Filter by country code"),
    base_type: Optional[str] = Query(None, description="Filter by base type"),
):
    """List known military bases worldwide."""
    cache_key = f"bases:{country or 'all'}:{base_type or 'all'}"

    cached = await cache_get(cache_key)
    if cached:
        return ListMilitaryBasesResponse(**cached)

    # Static data - would be loaded from Delta Lake
    bases = []

    result = {"bases": bases, "total": len(bases)}
    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return ListMilitaryBasesResponse(**result)


@router.get("/theater-posture/{theater}", response_model=TheaterPosture)
async def get_theater_posture(theater: str):
    """Get posture assessment for a military theater."""
    cache_key = f"posture:{theater}"

    cached = await cache_get(cache_key)
    if cached:
        return TheaterPosture(**cached)

    # Demo mode - AI assessment would go here
    posture = TheaterPosture(
        theater=theater,
        alert_level="low",
        active_flights=0,
        recent_incidents=0,
        assessment="No significant activity detected.",
    )

    await cache_set(cache_key, posture.model_dump(), 300)  # 5 minute cache
    return posture
