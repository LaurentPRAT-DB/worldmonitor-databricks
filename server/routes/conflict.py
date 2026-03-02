"""
Conflict API endpoints - ACLED, UCDP, humanitarian data.
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


class ConflictEvent(BaseModel):
    id: str
    event_type: str
    country: str
    admin1: Optional[str] = None
    location: Location
    occurred_at: int  # Unix timestamp ms
    fatalities: int = 0
    actors: list[str] = []
    source: Optional[str] = None


class ListAcledEventsResponse(BaseModel):
    events: list[ConflictEvent]
    total: int


class ListUcdpEventsResponse(BaseModel):
    events: list[ConflictEvent]
    total: int


class HumanitarianSummary(BaseModel):
    country: str
    displaced_total: int
    refugees: int
    idps: int  # Internally Displaced Persons
    asylum_seekers: int
    last_updated: str


# ACLED API configuration
ACLED_BASE_URL = "https://api.acleddata.com/acled/read"
ACLED_CACHE_TTL = 900  # 15 minutes


@router.get("/list-acled-events", response_model=ListAcledEventsResponse)
async def list_acled_events(
    start: Optional[int] = Query(None, description="Start timestamp (ms)"),
    end: Optional[int] = Query(None, description="End timestamp (ms)"),
    country: Optional[str] = Query(None, description="Country filter"),
    event_types: str = Query(
        "Battles|Explosions/Remote violence|Violence against civilians",
        description="Pipe-separated event types"
    ),
    limit: int = Query(1000, le=5000),
):
    """List ACLED conflict events within a time range."""
    cache_key = f"acled:{country or 'all'}:{start}:{end}"

    # Check cache first
    cached = await cache_get(cache_key)
    if cached:
        return ListAcledEventsResponse(**cached)

    # Calculate date range
    now = datetime.utcnow()
    start_date = datetime.fromtimestamp(start / 1000) if start else now - timedelta(days=30)
    end_date = datetime.fromtimestamp(end / 1000) if end else now

    # Fetch from ACLED API
    events = []
    if settings.ACLED_ACCESS_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "key": settings.ACLED_ACCESS_TOKEN,
                    "email": "api@worldmonitor.app",  # Required by ACLED
                    "event_date": f"{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}",
                    "event_date_where": "BETWEEN",
                    "event_type": event_types,
                    "limit": limit,
                }
                if country:
                    params["country"] = country

                response = await client.get(ACLED_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get("data", []):
                    try:
                        lat = float(item.get("latitude", 0))
                        lon = float(item.get("longitude", 0))
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            events.append(ConflictEvent(
                                id=f"acled-{item.get('event_id_cnty', '')}",
                                event_type=item.get("event_type", ""),
                                country=item.get("country", ""),
                                admin1=item.get("admin1"),
                                location=Location(latitude=lat, longitude=lon),
                                occurred_at=int(datetime.strptime(
                                    item.get("event_date", "1970-01-01"),
                                    "%Y-%m-%d"
                                ).timestamp() * 1000),
                                fatalities=int(item.get("fatalities", 0) or 0),
                                actors=[a for a in [item.get("actor1"), item.get("actor2")] if a],
                                source=item.get("source"),
                            ))
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"[acled] API error: {e}")

    result = {"events": [e.model_dump() for e in events], "total": len(events)}
    await cache_set(cache_key, result, ACLED_CACHE_TTL)
    return ListAcledEventsResponse(**result)


# UCDP API configuration
UCDP_BASE_URL = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"
UCDP_CACHE_TTL = 3600  # 1 hour


@router.get("/list-ucdp-events", response_model=ListUcdpEventsResponse)
async def list_ucdp_events(
    start: Optional[int] = Query(None, description="Start timestamp (ms)"),
    end: Optional[int] = Query(None, description="End timestamp (ms)"),
    country: Optional[str] = Query(None, description="Country filter"),
    limit: int = Query(1000, le=5000),
):
    """List UCDP georeferenced conflict events."""
    cache_key = f"ucdp:{country or 'all'}:{start}:{end}"

    cached = await cache_get(cache_key)
    if cached:
        return ListUcdpEventsResponse(**cached)

    now = datetime.utcnow()
    start_date = datetime.fromtimestamp(start / 1000) if start else now - timedelta(days=365)
    end_date = datetime.fromtimestamp(end / 1000) if end else now

    events = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "pagesize": min(limit, 1000),
                "StartDate": start_date.strftime("%Y-%m-%d"),
                "EndDate": end_date.strftime("%Y-%m-%d"),
            }
            if country:
                params["Country"] = country

            headers = {}
            if settings.UCDP_ACCESS_TOKEN:
                headers["Authorization"] = f"Bearer {settings.UCDP_ACCESS_TOKEN}"

            response = await client.get(UCDP_BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            for item in data.get("Result", []):
                try:
                    lat = float(item.get("latitude", 0))
                    lon = float(item.get("longitude", 0))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        events.append(ConflictEvent(
                            id=f"ucdp-{item.get('id', '')}",
                            event_type=item.get("type_of_violence", "Unknown"),
                            country=item.get("country", ""),
                            admin1=item.get("adm_1"),
                            location=Location(latitude=lat, longitude=lon),
                            occurred_at=int(datetime.strptime(
                                item.get("date_start", "1970-01-01"),
                                "%Y-%m-%d"
                            ).timestamp() * 1000),
                            fatalities=int(item.get("best", 0) or 0),
                            actors=[a for a in [item.get("side_a"), item.get("side_b")] if a],
                            source="UCDP",
                        ))
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        print(f"[ucdp] API error: {e}")

    result = {"events": [e.model_dump() for e in events], "total": len(events)}
    await cache_set(cache_key, result, UCDP_CACHE_TTL)
    return ListUcdpEventsResponse(**result)


# UNHCR API for displacement data
UNHCR_BASE_URL = "https://api.unhcr.org/population/v1"


@router.get("/humanitarian-summary/{country_code}", response_model=HumanitarianSummary)
async def get_humanitarian_summary(country_code: str):
    """Get humanitarian/displacement summary for a country."""
    cache_key = f"humanitarian:{country_code}"

    cached = await cache_get(cache_key)
    if cached:
        return HumanitarianSummary(**cached)

    summary = HumanitarianSummary(
        country=country_code,
        displaced_total=0,
        refugees=0,
        idps=0,
        asylum_seekers=0,
        last_updated=datetime.utcnow().isoformat(),
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get refugee data from UNHCR
            params = {
                "limit": 1,
                "coo": country_code,  # Country of origin
                "year": datetime.utcnow().year,
            }
            response = await client.get(f"{UNHCR_BASE_URL}/population/", params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    summary.refugees = int(item.get("refugees", 0) or 0)
                    summary.asylum_seekers = int(item.get("asylum_seekers", 0) or 0)
                    summary.idps = int(item.get("idps", 0) or 0)
                    summary.displaced_total = summary.refugees + summary.asylum_seekers + summary.idps
    except Exception as e:
        print(f"[unhcr] API error: {e}")

    result = summary.model_dump()
    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return summary
