"""
Conflict API endpoints - ACLED, UCDP, humanitarian data.

STORAGE PATTERN: Lakebase-first for UCDP (free API)
- Fresh data fetched from APIs and persisted to Lakebase
- Subsequent queries served from Lakebase for low latency
- 30-day retention in Lakebase
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..config import settings
from ..db import (
    cache_get,
    cache_set,
    db,
    save_conflict_events_batch,
    get_conflicts_from_lakebase,
    RETENTION_HOURS,
)

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


# ACLED API configuration (OAuth system as of Sept 2025)
ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_API_URL = "https://acleddata.com/acleddatanew/api/acled/read"
ACLED_CACHE_TTL = 900  # 15 minutes

# Token cache (valid for 24 hours, we refresh every 23 hours to be safe)
_acled_token_cache: dict = {"token": None, "expires_at": 0}


async def get_acled_oauth_token() -> str | None:
    """Get OAuth access token from ACLED API.

    Tokens are valid for 24 hours. We cache and reuse them.
    Returns None if credentials are not configured or auth fails.
    """
    import time

    # Check cache first
    if _acled_token_cache["token"] and time.time() < _acled_token_cache["expires_at"]:
        return _acled_token_cache["token"]

    # Need credentials
    if not settings.ACLED_EMAIL or not settings.ACLED_PASSWORD:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ACLED_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "username": settings.ACLED_EMAIL,
                    "password": settings.ACLED_PASSWORD,
                    "grant_type": "password",
                    "client_id": "acled",
                },
            )
            if response.status_code != 200:
                print(f"[acled] OAuth token request failed: {response.status_code}")
                return None

            token_data = response.json()
            token = token_data.get("access_token")
            if token:
                # Cache for 23 hours (tokens valid for 24 hours)
                _acled_token_cache["token"] = token
                _acled_token_cache["expires_at"] = time.time() + (23 * 60 * 60)
                print("[acled] OAuth token obtained successfully")
            return token
    except Exception as e:
        print(f"[acled] OAuth error: {e}")
        return None


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

    # Fetch from ACLED API using OAuth
    events = []
    token = await get_acled_oauth_token()
    if token:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "event_date": f"{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}",
                    "event_date_where": "BETWEEN",
                    "event_type": event_types,
                    "limit": limit,
                }
                if country:
                    params["country"] = country

                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(ACLED_API_URL, params=params, headers=headers)
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
    else:
        print("[acled] No OAuth token available - check ACLED_EMAIL and ACLED_PASSWORD")

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
    force_refresh: bool = Query(False, description="Force refresh from API, skip Lakebase cache"),
):
    """List UCDP georeferenced conflict events.

    LAKEBASE-FIRST PATTERN:
    1. Check Lakebase for recent UCDP data
    2. If data is fresh enough, return from Lakebase
    3. If stale or missing, fetch from UCDP API and persist to Lakebase

    NOTE: UCDP data is historical (up to ~2023), not real-time.
    Default range is 2019-2023 if no date filter provided.
    """
    # UCDP GED 24.1 dataset covers up to end of 2023
    UCDP_MAX_DATE = datetime(2023, 12, 31)
    now = datetime.utcnow()

    # Default to 2019-2023 for historical conflict data
    start_date = datetime.fromtimestamp(start / 1000) if start else datetime(2019, 1, 1)
    end_date = datetime.fromtimestamp(end / 1000) if end else UCDP_MAX_DATE

    # Cap end date at UCDP data availability
    if end_date > UCDP_MAX_DATE:
        end_date = UCDP_MAX_DATE
    hours_back = int((now - start_date).total_seconds() / 3600)

    # Try Lakebase first (fast path) - skip if force_refresh requested
    if not db.is_demo_mode and not force_refresh:
        lakebase_data = await get_conflicts_from_lakebase(hours_back, source="ucdp", country=country)
        if lakebase_data:
            print(f"[ucdp] Serving {len(lakebase_data)} events from Lakebase")
            events = [
                ConflictEvent(
                    id=e["id"],
                    event_type=e["event_type"],
                    country=e["country"],
                    admin1=e.get("admin1"),
                    location=Location(**e["location"]),
                    occurred_at=e["occurred_at"],
                    fatalities=e["fatalities"],
                    actors=e["actors"],
                    source="UCDP",
                )
                for e in lakebase_data[:limit]
            ]
            return ListUcdpEventsResponse(events=events, total=len(events))

    # Fallback: Check cache
    cache_key = f"ucdp:{country or 'all'}:{start}:{end}"
    cached = await cache_get(cache_key)
    if cached:
        return ListUcdpEventsResponse(**cached)

    # Fetch from UCDP API
    events = []
    events_to_persist = []

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
                # UCDP requires the token in the x-ucdp-access-token header
                headers["x-ucdp-access-token"] = settings.UCDP_ACCESS_TOKEN

            response = await client.get(UCDP_BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            for item in data.get("Result", []):
                try:
                    lat = float(item.get("latitude", 0))
                    lon = float(item.get("longitude", 0))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        event_id = f"ucdp-{item.get('id', '')}"
                        occurred_at = int(datetime.strptime(
                            item.get("date_start", "1970-01-01"),
                            "%Y-%m-%d"
                        ).timestamp() * 1000)

                        # UCDP type_of_violence: 1=state-based, 2=non-state, 3=one-sided
                        violence_type_map = {
                            1: "State-based conflict",
                            2: "Non-state conflict",
                            3: "One-sided violence",
                        }
                        violence_type = item.get("type_of_violence", 0)
                        event_type = violence_type_map.get(violence_type, f"Type {violence_type}")

                        events.append(ConflictEvent(
                            id=event_id,
                            event_type=event_type,
                            country=item.get("country", ""),
                            admin1=item.get("adm_1"),
                            location=Location(latitude=lat, longitude=lon),
                            occurred_at=occurred_at,
                            fatalities=int(item.get("best", 0) or 0),
                            actors=[a for a in [item.get("side_a"), item.get("side_b")] if a],
                            source="UCDP",
                        ))

                        # Prepare for Lakebase persistence
                        # Note: where_prec is precision level (1-6), not location name
                        # Use where_coordinates or location for actual location description
                        location_name = item.get("where_coordinates") or item.get("location")
                        if location_name and not isinstance(location_name, str):
                            location_name = str(location_name)

                        events_to_persist.append({
                            "id": event_id,
                            "source": "ucdp",
                            "event_type": event_type,
                            "country": item.get("country", ""),
                            "admin1": item.get("adm_1"),
                            "location_name": location_name,
                            "latitude": lat,
                            "longitude": lon,
                            "occurred_at": occurred_at,
                            "fatalities": int(item.get("best", 0) or 0),
                            "actors": [a for a in [item.get("side_a"), item.get("side_b")] if a],
                            "notes": item.get("source_headline"),
                        })
                except (ValueError, TypeError):
                    continue

        # Persist to Lakebase
        if events_to_persist and not db.is_demo_mode:
            saved = await save_conflict_events_batch(events_to_persist)
            print(f"[ucdp] Persisted {saved} events to Lakebase")

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
