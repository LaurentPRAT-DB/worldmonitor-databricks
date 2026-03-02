"""
Infrastructure API endpoints - Internet outages and service status.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..config import settings
from ..db import cache_get, cache_set

router = APIRouter()


class Location(BaseModel):
    latitude: float
    longitude: float


class InternetOutage(BaseModel):
    id: str
    country: str
    country_code: str
    location: Optional[Location] = None
    asn: Optional[int] = None
    asn_name: Optional[str] = None
    start_time: int
    end_time: Optional[int] = None
    severity: str  # minor, moderate, major
    source: str


class ListInternetOutagesResponse(BaseModel):
    outages: list[InternetOutage]
    total: int
    updated_at: int


class ServiceStatus(BaseModel):
    service: str
    status: str  # operational, degraded, outage
    last_checked: int
    response_time_ms: Optional[int] = None
    url: str


class ListServiceStatusesResponse(BaseModel):
    services: list[ServiceStatus]
    updated_at: int


# Cloudflare Radar API
CLOUDFLARE_RADAR_URL = "https://api.cloudflare.com/client/v4/radar"
OUTAGE_CACHE_TTL = 300  # 5 minutes

# Services to monitor
MONITORED_SERVICES = [
    ("GitHub", "https://www.githubstatus.com/api/v2/status.json"),
    ("AWS", "https://status.aws.amazon.com"),
    ("Google Cloud", "https://status.cloud.google.com"),
    ("Azure", "https://status.azure.com/en-us/status"),
    ("Cloudflare", "https://www.cloudflarestatus.com/api/v2/status.json"),
    ("OpenAI", "https://status.openai.com/api/v2/status.json"),
]


@router.get("/list-internet-outages", response_model=ListInternetOutagesResponse)
async def list_internet_outages(
    country: Optional[str] = Query(None, description="Filter by country code"),
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back"),
):
    """List internet outages from Cloudflare Radar."""
    cache_key = f"outages:{country or 'all'}:{hours_back}"

    cached = await cache_get(cache_key)
    if cached:
        return ListInternetOutagesResponse(**cached)

    outages = []
    now = datetime.utcnow()

    if settings.CLOUDFLARE_API_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
                }

                # Query Cloudflare Radar annotations API
                response = await client.get(
                    f"{CLOUDFLARE_RADAR_URL}/annotations/outages",
                    headers=headers,
                    params={
                        "dateRange": f"{hours_back}h",
                        "format": "json",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("result", {}).get("annotations", []):
                        # Filter by country if specified
                        item_country = item.get("asn", {}).get("country")
                        if country and item_country != country:
                            continue

                        outages.append(InternetOutage(
                            id=str(item.get("id", "")),
                            country=item.get("country", "Unknown"),
                            country_code=item_country or "XX",
                            asn=item.get("asn", {}).get("asn"),
                            asn_name=item.get("asn", {}).get("name"),
                            start_time=int(datetime.fromisoformat(
                                item.get("startDate", now.isoformat()).replace("Z", "+00:00")
                            ).timestamp() * 1000),
                            end_time=int(datetime.fromisoformat(
                                item.get("endDate").replace("Z", "+00:00")
                            ).timestamp() * 1000) if item.get("endDate") else None,
                            severity=item.get("severity", "moderate"),
                            source="Cloudflare Radar",
                        ))
        except Exception as e:
            print(f"[cloudflare] API error: {e}")

    result = {
        "outages": [o.model_dump() for o in outages],
        "total": len(outages),
        "updated_at": int(now.timestamp() * 1000)
    }
    await cache_set(cache_key, result, OUTAGE_CACHE_TTL)
    return ListInternetOutagesResponse(**result)


@router.get("/list-service-statuses", response_model=ListServiceStatusesResponse)
async def list_service_statuses():
    """Check status of major cloud services."""
    cache_key = "services:status"

    cached = await cache_get(cache_key)
    if cached:
        return ListServiceStatusesResponse(**cached)

    services = []
    now = int(datetime.utcnow().timestamp() * 1000)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in MONITORED_SERVICES:
            status = "operational"
            response_time = None

            try:
                start = datetime.utcnow()
                response = await client.get(url)
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                response_time = int(elapsed)

                # Check for status page JSON
                if response.status_code == 200 and "status" in url:
                    try:
                        data = response.json()
                        indicator = data.get("status", {}).get("indicator", "none")
                        if indicator == "none":
                            status = "operational"
                        elif indicator == "minor":
                            status = "degraded"
                        else:
                            status = "outage"
                    except Exception:
                        pass
                elif response.status_code >= 500:
                    status = "outage"
                elif response.status_code >= 400:
                    status = "degraded"
            except httpx.TimeoutException:
                status = "degraded"
                response_time = 10000
            except Exception:
                status = "unknown"

            services.append(ServiceStatus(
                service=name,
                status=status,
                last_checked=now,
                response_time_ms=response_time,
                url=url,
            ))

    result = {
        "services": [s.model_dump() for s in services],
        "updated_at": now
    }
    await cache_set(cache_key, result, 60)  # 1 minute cache
    return ListServiceStatusesResponse(**result)
