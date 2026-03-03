"""
Cyber API endpoints - Threat intelligence IOCs from abuse.ch feeds.

Uses publicly available download endpoints:
- URLhaus CSV: Malicious URLs
- ThreatFox JSON: IOCs (IPs, domains, URLs, hashes)
- FeodoTracker JSON: Botnet C2 IPs
"""

from typing import Optional
from datetime import datetime, timedelta
from io import StringIO
import csv
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


# abuse.ch public download endpoints (no authentication required)
URLHAUS_CSV_URL = "https://urlhaus.abuse.ch/downloads/csv_recent/"
THREATFOX_JSON_URL = "https://threatfox.abuse.ch/export/json/recent/"
FEODO_JSON_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
CYBER_CACHE_TTL = 900  # 15 minutes


def parse_urlhaus_csv(csv_content: str, days_back: int, limit: int) -> list[ThreatIOC]:
    """Parse URLhaus CSV format into ThreatIOC objects."""
    threats = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days_back)

    # Skip header lines starting with #
    lines = [line for line in csv_content.split('\n') if line and not line.startswith('#')]

    if not lines:
        return []

    # Parse CSV
    reader = csv.reader(StringIO('\n'.join(lines)))
    for row in reader:
        if len(row) < 8:
            continue

        try:
            # CSV format: id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter
            ioc_id = row[0].strip('"')
            date_added = row[1].strip('"')
            url = row[2].strip('"')
            threat = row[5].strip('"') if len(row) > 5 else "malware_download"
            tags_str = row[6].strip('"') if len(row) > 6 else ""
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]

            # Parse date
            try:
                first_seen = datetime.strptime(date_added, "%Y-%m-%d %H:%M:%S")
                if first_seen < cutoff:
                    continue
            except Exception:
                first_seen = now

            threats.append(ThreatIOC(
                id=f"urlhaus-{ioc_id}",
                ioc_type="url",
                ioc_value=url,
                threat_type=threat,
                malware_family=tags[0] if tags else None,
                confidence=80,
                first_seen=int(first_seen.timestamp() * 1000),
                last_seen=int(now.timestamp() * 1000),
                source="URLhaus",
                tags=tags,
            ))

            if len(threats) >= limit:
                break

        except Exception as e:
            print(f"[cyber] Error parsing URLhaus row: {e}")
            continue

    return threats


def parse_threatfox_json(data: dict, days_back: int, limit: int, ioc_type_filter: Optional[str]) -> list[ThreatIOC]:
    """Parse ThreatFox JSON format into ThreatIOC objects."""
    threats = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days_back)

    # ThreatFox returns dict with IOC IDs as keys
    for ioc_id, items in data.items():
        if not isinstance(items, list):
            continue

        for item in items:
            try:
                ioc_value = item.get("ioc_value", "")
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

                if ioc_type_filter and ioc_type_filter != mapped_type:
                    continue

                # Parse date
                try:
                    first_seen = datetime.strptime(
                        item.get("first_seen_utc", "1970-01-01 00:00:00"),
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if first_seen < cutoff:
                        continue
                except Exception:
                    first_seen = now

                # Parse tags from string
                tags_str = item.get("tags", "")
                tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []

                threats.append(ThreatIOC(
                    id=f"threatfox-{ioc_id}",
                    ioc_type=mapped_type,
                    ioc_value=ioc_value,
                    threat_type=item.get("threat_type", "unknown"),
                    malware_family=item.get("malware_printable"),
                    confidence=int(item.get("confidence_level", 50)),
                    first_seen=int(first_seen.timestamp() * 1000),
                    last_seen=int(now.timestamp() * 1000),
                    source="ThreatFox",
                    tags=tags,
                ))

                if len(threats) >= limit:
                    return threats

            except Exception as e:
                print(f"[cyber] Error parsing ThreatFox item: {e}")
                continue

    return threats


def parse_feodo_json(data: list, limit: int) -> list[ThreatIOC]:
    """Parse FeodoTracker JSON format into ThreatIOC objects."""
    threats = []
    now = datetime.utcnow()

    for item in data[:limit]:
        try:
            ip = item.get("ip_address", "")
            port = item.get("port", "")
            ioc_value = f"{ip}:{port}" if port else ip

            # Parse date
            try:
                first_seen = datetime.strptime(
                    item.get("first_seen", "1970-01-01 00:00:00"),
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                first_seen = now

            threats.append(ThreatIOC(
                id=f"feodo-{ip.replace('.', '-')}-{port}",
                ioc_type="ip",
                ioc_value=ioc_value,
                threat_type="botnet_cc",
                malware_family=item.get("malware"),
                confidence=90,
                first_seen=int(first_seen.timestamp() * 1000),
                last_seen=int(now.timestamp() * 1000),
                source="FeodoTracker",
                tags=[item.get("as_name", ""), item.get("country", "")],
            ))

        except Exception as e:
            print(f"[cyber] Error parsing Feodo item: {e}")
            continue

    return threats


@router.get("/list-cyber-threats", response_model=ListCyberThreatsResponse)
async def list_cyber_threats(
    ioc_type: Optional[str] = Query(None, description="Filter by IOC type: url, ip, domain, hash"),
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    days_back: int = Query(7, ge=1, le=30),
    limit: int = Query(100, le=1000),
):
    """
    List cyber threat IOCs from abuse.ch feeds.

    Sources:
    - URLhaus: Malicious URLs used for malware distribution
    - ThreatFox: IOCs (IPs, domains, URLs, hashes) from various malware families
    - FeodoTracker: Botnet C2 IP addresses

    All data is publicly available without authentication.
    """
    cache_key = f"cyber:{ioc_type or 'all'}:{threat_type or 'all'}:{days_back}"

    cached = await cache_get(cache_key)
    if cached:
        return ListCyberThreatsResponse(**cached)

    threats = []
    now = datetime.utcnow()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch from URLhaus CSV (malicious URLs)
        if not ioc_type or ioc_type == "url":
            try:
                response = await client.get(URLHAUS_CSV_URL)
                if response.status_code == 200:
                    urlhaus_threats = parse_urlhaus_csv(response.text, days_back, limit)
                    threats.extend(urlhaus_threats)
                    print(f"[cyber] URLhaus: fetched {len(urlhaus_threats)} threats")
            except Exception as e:
                print(f"[cyber] URLhaus error: {e}")

        # Fetch from ThreatFox JSON
        try:
            response = await client.get(THREATFOX_JSON_URL)
            if response.status_code == 200:
                data = response.json()
                threatfox_threats = parse_threatfox_json(data, days_back, limit, ioc_type)
                threats.extend(threatfox_threats)
                print(f"[cyber] ThreatFox: fetched {len(threatfox_threats)} threats")
        except Exception as e:
            print(f"[cyber] ThreatFox error: {e}")

        # Fetch from FeodoTracker JSON (botnet C2 IPs)
        if not ioc_type or ioc_type == "ip":
            try:
                response = await client.get(FEODO_JSON_URL)
                if response.status_code == 200:
                    data = response.json()
                    feodo_threats = parse_feodo_json(data, limit)
                    threats.extend(feodo_threats)
                    print(f"[cyber] FeodoTracker: fetched {len(feodo_threats)} threats")
            except Exception as e:
                print(f"[cyber] FeodoTracker error: {e}")

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
