"""
Cyber API endpoints - Threat intelligence IOCs.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..db import cache_get, cache_set

router = APIRouter()


class ThreatIOC(BaseModel):
    id: str
    ioc_type: str  # url, domain, ip, hash
    ioc_value: str
    threat_type: str
    malware_family: Optional[str] = None
    confidence: int  # 0-100
    first_seen: int
    last_seen: int
    source: str
    tags: list[str] = []


class ListCyberThreatsResponse(BaseModel):
    threats: list[ThreatIOC]
    total: int
    updated_at: int


class ThreatStats(BaseModel):
    total_iocs: int
    by_type: dict[str, int]
    by_threat: dict[str, int]
    updated_at: int


# URLhaus API (free, no key required)
URLHAUS_BASE_URL = "https://urlhaus-api.abuse.ch/v1"
THREATFOX_BASE_URL = "https://threatfox-api.abuse.ch/api/v1"
CYBER_CACHE_TTL = 900  # 15 minutes


@router.get("/list-cyber-threats", response_model=ListCyberThreatsResponse)
async def list_cyber_threats(
    ioc_type: Optional[str] = Query(None, description="Filter by IOC type"),
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    days_back: int = Query(7, ge=1, le=30),
    limit: int = Query(100, le=1000),
):
    """List cyber threat IOCs from abuse.ch feeds."""
    cache_key = f"cyber:{ioc_type or 'all'}:{threat_type or 'all'}:{days_back}"

    cached = await cache_get(cache_key)
    if cached:
        return ListCyberThreatsResponse(**cached)

    threats = []
    now = datetime.utcnow()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch from URLhaus (malicious URLs)
            response = await client.post(
                f"{URLHAUS_BASE_URL}/urls/recent/",
                data={"limit": min(limit, 100)},
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get("urls", []):
                    if ioc_type and ioc_type != "url":
                        continue

                    # Parse dates
                    try:
                        first_seen = datetime.strptime(
                            item.get("dateadded", "1970-01-01 00:00:00"),
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if (now - first_seen) > timedelta(days=days_back):
                            continue
                    except Exception:
                        first_seen = now

                    threats.append(ThreatIOC(
                        id=str(item.get("id", "")),
                        ioc_type="url",
                        ioc_value=item.get("url", ""),
                        threat_type=item.get("threat", "malware"),
                        malware_family=item.get("tags", [None])[0] if item.get("tags") else None,
                        confidence=80,
                        first_seen=int(first_seen.timestamp() * 1000),
                        last_seen=int(now.timestamp() * 1000),
                        source="URLhaus",
                        tags=item.get("tags", []),
                    ))

            # Fetch from ThreatFox (IOCs)
            response = await client.post(
                THREATFOX_BASE_URL,
                json={"query": "get_iocs", "days": min(days_back, 7)},
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get("data", [])[:limit]:
                    item_type = item.get("ioc_type", "")

                    # Map ThreatFox types to our types
                    if "ip" in item_type.lower():
                        mapped_type = "ip"
                    elif "domain" in item_type.lower():
                        mapped_type = "domain"
                    elif "url" in item_type.lower():
                        mapped_type = "url"
                    elif "hash" in item_type.lower() or "md5" in item_type.lower() or "sha" in item_type.lower():
                        mapped_type = "hash"
                    else:
                        mapped_type = "other"

                    if ioc_type and ioc_type != mapped_type:
                        continue

                    try:
                        first_seen = datetime.strptime(
                            item.get("first_seen", "1970-01-01 00:00:00 UTC"),
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    except Exception:
                        first_seen = now

                    threats.append(ThreatIOC(
                        id=str(item.get("id", "")),
                        ioc_type=mapped_type,
                        ioc_value=item.get("ioc", ""),
                        threat_type=item.get("threat_type", "unknown"),
                        malware_family=item.get("malware_printable"),
                        confidence=int(item.get("confidence_level", 50)),
                        first_seen=int(first_seen.timestamp() * 1000),
                        last_seen=int(now.timestamp() * 1000),
                        source="ThreatFox",
                        tags=item.get("tags", []) or [],
                    ))

    except Exception as e:
        print(f"[cyber] API error: {e}")

    # Filter by threat type if specified
    if threat_type:
        threats = [t for t in threats if threat_type.lower() in t.threat_type.lower()]

    # Sort by first_seen (newest first) and limit
    threats.sort(key=lambda t: t.first_seen, reverse=True)
    threats = threats[:limit]

    result = {
        "threats": [t.model_dump() for t in threats],
        "total": len(threats),
        "updated_at": int(now.timestamp() * 1000)
    }
    await cache_set(cache_key, result, CYBER_CACHE_TTL)
    return ListCyberThreatsResponse(**result)


@router.get("/threat-stats", response_model=ThreatStats)
async def get_threat_stats():
    """Get aggregated threat statistics."""
    cache_key = "cyber:stats"

    cached = await cache_get(cache_key)
    if cached:
        return ThreatStats(**cached)

    # Get all threats from the last 7 days
    response = await list_cyber_threats(days_back=7, limit=500)

    by_type: dict[str, int] = {}
    by_threat: dict[str, int] = {}

    for threat in response.threats:
        by_type[threat.ioc_type] = by_type.get(threat.ioc_type, 0) + 1
        by_threat[threat.threat_type] = by_threat.get(threat.threat_type, 0) + 1

    stats = ThreatStats(
        total_iocs=response.total,
        by_type=by_type,
        by_threat=by_threat,
        updated_at=int(datetime.utcnow().timestamp() * 1000),
    )

    await cache_set(cache_key, stats.model_dump(), 3600)  # 1 hour cache
    return stats
