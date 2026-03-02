"""
Maritime API endpoints - AIS vessel tracking.

SYNTHETIC DATA MODE:
- When USE_SYNTHETIC_MARITIME_DATA=True, returns demo vessel data
- Synthetic vessels use MMSI prefix "999" (invalid in real AIS)
- All synthetic vessels have is_synthetic=True flag
- Response includes data_source="synthetic" field
- To disable: set USE_SYNTHETIC_MARITIME_DATA=False in config or env
"""

import os
import random
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import (
    cache_get,
    cache_set,
    save_vessel_positions_batch,
    get_vessel_route,
    get_all_vessel_routes,
    db,
)

router = APIRouter()

# Configuration: Set to False when real AIS data source is available
USE_SYNTHETIC_MARITIME_DATA = os.environ.get("USE_SYNTHETIC_MARITIME_DATA", "true").lower() == "true"

# Synthetic vessel data - realistic positions in major shipping lanes
# MMSI prefix "999" indicates synthetic data (not valid in real AIS)
SYNTHETIC_VESSELS = [
    # Mediterranean Sea
    {"mmsi": "244650123", "name": "MAERSK SEALAND", "ship_type": 70, "flag": "NL", "lat": 35.9, "lon": 14.5, "speed": 18.5, "course": 90, "dest": "PIRAEUS"},
    {"mmsi": "636091234", "name": "MSC GENEVA", "ship_type": 70, "flag": "LR", "lat": 36.2, "lon": 5.3, "speed": 16.2, "course": 75, "dest": "BARCELONA"},
    {"mmsi": "538006789", "name": "COSCO SHIPPING", "ship_type": 70, "flag": "MH", "lat": 34.5, "lon": 28.9, "speed": 14.8, "course": 280, "dest": "SUEZ"},
    # English Channel
    {"mmsi": "235089012", "name": "DOVER SPIRIT", "ship_type": 60, "flag": "GB", "lat": 51.0, "lon": 1.4, "speed": 12.5, "course": 220, "dest": "CALAIS"},
    {"mmsi": "227345678", "name": "NORMANDIE EXPRESS", "ship_type": 60, "flag": "FR", "lat": 50.8, "lon": 0.9, "speed": 22.0, "course": 180, "dest": "LE HAVRE"},
    # North Sea
    {"mmsi": "211234567", "name": "HAMBURG BRIDGE", "ship_type": 70, "flag": "DE", "lat": 54.2, "lon": 7.8, "speed": 15.3, "course": 315, "dest": "HAMBURG"},
    {"mmsi": "245678901", "name": "ROTTERDAM EXPRESS", "ship_type": 70, "flag": "NL", "lat": 52.5, "lon": 4.0, "speed": 11.2, "course": 90, "dest": "ROTTERDAM"},
    # Atlantic - US East Coast
    {"mmsi": "367890123", "name": "ATLANTIC STAR", "ship_type": 70, "flag": "US", "lat": 40.5, "lon": -73.8, "speed": 8.5, "course": 270, "dest": "NEW YORK"},
    {"mmsi": "368012345", "name": "CHARLESTON CARRIER", "ship_type": 70, "flag": "US", "lat": 32.8, "lon": -79.9, "speed": 10.2, "course": 180, "dest": "CHARLESTON"},
    {"mmsi": "338123456", "name": "MIAMI TRADER", "ship_type": 70, "flag": "US", "lat": 25.8, "lon": -80.1, "speed": 12.0, "course": 90, "dest": "MIAMI"},
    # Gulf of Mexico
    {"mmsi": "367234567", "name": "GULF PIONEER", "ship_type": 80, "flag": "US", "lat": 29.0, "lon": -89.5, "speed": 6.5, "course": 45, "dest": "NEW ORLEANS"},
    {"mmsi": "345678012", "name": "HOUSTON OIL", "ship_type": 80, "flag": "PA", "lat": 28.5, "lon": -94.2, "speed": 8.0, "course": 350, "dest": "HOUSTON"},
    # Caribbean
    {"mmsi": "352345678", "name": "CARIBBEAN QUEEN", "ship_type": 60, "flag": "PA", "lat": 18.5, "lon": -66.1, "speed": 15.5, "course": 270, "dest": "SAN JUAN"},
    {"mmsi": "309456789", "name": "BAHAMAS EXPRESS", "ship_type": 60, "flag": "BS", "lat": 25.1, "lon": -77.3, "speed": 18.0, "course": 180, "dest": "NASSAU"},
    # Pacific - US West Coast
    {"mmsi": "366789012", "name": "PACIFIC NAVIGATOR", "ship_type": 70, "flag": "US", "lat": 33.7, "lon": -118.3, "speed": 14.5, "course": 270, "dest": "LOS ANGELES"},
    {"mmsi": "369012345", "name": "OAKLAND BRIDGE", "ship_type": 70, "flag": "US", "lat": 37.8, "lon": -122.4, "speed": 10.0, "course": 90, "dest": "OAKLAND"},
    {"mmsi": "367345678", "name": "SEATTLE TRADER", "ship_type": 70, "flag": "US", "lat": 47.6, "lon": -122.4, "speed": 8.5, "course": 180, "dest": "SEATTLE"},
    # Asia - South China Sea
    {"mmsi": "413456789", "name": "SHANGHAI EXPRESS", "ship_type": 70, "flag": "CN", "lat": 22.3, "lon": 114.2, "speed": 16.8, "course": 45, "dest": "HONG KONG"},
    {"mmsi": "416789012", "name": "SHENZHEN STAR", "ship_type": 70, "flag": "CN", "lat": 21.5, "lon": 113.8, "speed": 18.2, "course": 90, "dest": "SHENZHEN"},
    {"mmsi": "533012345", "name": "SINGAPORE SPIRIT", "ship_type": 70, "flag": "SG", "lat": 1.3, "lon": 103.8, "speed": 12.5, "course": 270, "dest": "SINGAPORE"},
    {"mmsi": "548234567", "name": "MANILA BAY", "ship_type": 70, "flag": "PH", "lat": 14.5, "lon": 120.9, "speed": 11.0, "course": 180, "dest": "MANILA"},
    # Japan/Korea
    {"mmsi": "431567890", "name": "TOKYO MARU", "ship_type": 70, "flag": "JP", "lat": 35.4, "lon": 139.8, "speed": 14.0, "course": 90, "dest": "TOKYO"},
    {"mmsi": "440678901", "name": "BUSAN CONTAINER", "ship_type": 70, "flag": "KR", "lat": 35.1, "lon": 129.0, "speed": 15.5, "course": 270, "dest": "BUSAN"},
    # Middle East / Suez
    {"mmsi": "470789012", "name": "DUBAI MERCHANT", "ship_type": 80, "flag": "AE", "lat": 25.3, "lon": 55.3, "speed": 10.5, "course": 180, "dest": "DUBAI"},
    {"mmsi": "622890123", "name": "SUEZ TRANSPORTER", "ship_type": 70, "flag": "EG", "lat": 30.0, "lon": 32.5, "speed": 8.0, "course": 0, "dest": "PORT SAID"},
    {"mmsi": "403901234", "name": "PERSIAN GULF", "ship_type": 80, "flag": "SA", "lat": 26.5, "lon": 50.2, "speed": 12.0, "course": 90, "dest": "DAMMAM"},
    # Indian Ocean
    {"mmsi": "419012345", "name": "MUMBAI CARRIER", "ship_type": 70, "flag": "IN", "lat": 18.9, "lon": 72.8, "speed": 13.5, "course": 270, "dest": "MUMBAI"},
    {"mmsi": "565123456", "name": "COLOMBO TRADER", "ship_type": 70, "flag": "LK", "lat": 6.9, "lon": 79.9, "speed": 11.0, "course": 180, "dest": "COLOMBO"},
    # Africa
    {"mmsi": "601234567", "name": "CAPE TOWN EXPRESS", "ship_type": 70, "flag": "ZA", "lat": -33.9, "lon": 18.4, "speed": 14.0, "course": 90, "dest": "CAPE TOWN"},
    {"mmsi": "627345678", "name": "DURBAN STAR", "ship_type": 70, "flag": "ZA", "lat": -29.9, "lon": 31.0, "speed": 12.5, "course": 180, "dest": "DURBAN"},
    # Australia
    {"mmsi": "503456789", "name": "SYDNEY HARBOUR", "ship_type": 70, "flag": "AU", "lat": -33.8, "lon": 151.2, "speed": 10.0, "course": 90, "dest": "SYDNEY"},
    {"mmsi": "503567890", "name": "MELBOURNE TRADER", "ship_type": 70, "flag": "AU", "lat": -37.8, "lon": 144.9, "speed": 11.5, "course": 270, "dest": "MELBOURNE"},
    # South America
    {"mmsi": "710678901", "name": "SANTOS PIONEER", "ship_type": 70, "flag": "BR", "lat": -23.9, "lon": -46.3, "speed": 13.0, "course": 180, "dest": "SANTOS"},
    {"mmsi": "725789012", "name": "BUENOS AIRES", "ship_type": 70, "flag": "AR", "lat": -34.6, "lon": -58.4, "speed": 9.5, "course": 90, "dest": "BUENOS AIRES"},
    {"mmsi": "730890123", "name": "VALPARAISO STAR", "ship_type": 70, "flag": "CL", "lat": -33.0, "lon": -71.6, "speed": 12.0, "course": 0, "dest": "VALPARAISO"},
    # Panama Canal
    {"mmsi": "352901234", "name": "CANAL NAVIGATOR", "ship_type": 70, "flag": "PA", "lat": 9.0, "lon": -79.5, "speed": 8.0, "course": 315, "dest": "PANAMA"},
    # Tankers in key areas
    {"mmsi": "538112233", "name": "CRUDE CARRIER", "ship_type": 80, "flag": "MH", "lat": 12.5, "lon": 43.5, "speed": 12.0, "course": 180, "dest": "BAB EL MANDEB"},
    {"mmsi": "538223344", "name": "LNG PIONEER", "ship_type": 81, "flag": "MH", "lat": 29.5, "lon": 48.5, "speed": 14.5, "course": 270, "dest": "KUWAIT"},
    {"mmsi": "477334455", "name": "VLCC TITAN", "ship_type": 80, "flag": "HK", "lat": 10.5, "lon": 107.0, "speed": 13.0, "course": 45, "dest": "VUNG TAU"},
]

# Ship type mapping
SHIP_TYPES = {
    60: "Passenger",
    70: "Cargo",
    80: "Tanker",
    81: "LNG Tanker",
}


class Position(BaseModel):
    latitude: float
    longitude: float


class Vessel(BaseModel):
    mmsi: str
    imo: Optional[str] = None
    name: Optional[str] = None
    ship_type: int = 0
    flag_country: Optional[str] = None
    position: Position
    course: float = 0
    speed: float = 0
    heading: int = 0
    nav_status: int = 0
    destination: Optional[str] = None
    timestamp: int
    is_synthetic: bool = False  # True for demo/synthetic data


class ListVesselsResponse(BaseModel):
    vessels: list[Vessel]
    total: int
    updated_at: int
    data_source: str = "real"  # "synthetic" or "real"


class VesselSnapshot(BaseModel):
    vessels: list[Vessel]
    bounding_box: Optional[dict] = None
    timestamp: int
    data_source: str = "real"  # "synthetic" or "real"


class RoutePoint(BaseModel):
    latitude: float
    longitude: float
    speed: float = 0
    course: float = 0
    recorded_at: Optional[str] = None


class VesselRoute(BaseModel):
    mmsi: str
    name: Optional[str] = None
    route: list[RoutePoint]
    total_points: int


class VesselRoutesResponse(BaseModel):
    routes: dict[str, list[RoutePoint]]
    time_range_hours: int
    total_vessels: int


def _generate_synthetic_vessels() -> list[Vessel]:
    """Generate synthetic vessel data with slight position variations.

    Synthetic vessels are marked with:
    - MMSI prefix "999" (invalid in real AIS system)
    - is_synthetic=True flag
    - Name suffix "[DEMO]"
    """
    now = int(datetime.utcnow().timestamp() * 1000)
    vessels = []

    for idx, v in enumerate(SYNTHETIC_VESSELS):
        # Add slight random variation to simulate movement
        lat_offset = random.uniform(-0.05, 0.05)
        lon_offset = random.uniform(-0.05, 0.05)
        speed_variation = random.uniform(-2, 2)

        # Use 999 prefix for synthetic MMSI (invalid in real AIS)
        synthetic_mmsi = f"999{idx:06d}"

        vessel = Vessel(
            mmsi=synthetic_mmsi,
            name=f"{v['name']} [DEMO]",  # Mark name as demo
            ship_type=v["ship_type"],
            flag_country=v["flag"],
            position=Position(
                latitude=v["lat"] + lat_offset,
                longitude=v["lon"] + lon_offset
            ),
            course=v["course"] + random.uniform(-5, 5),
            speed=max(0, v["speed"] + speed_variation),
            heading=int(v["course"]),
            nav_status=0,  # Under way using engine
            destination=v["dest"],
            timestamp=now - random.randint(0, 300000),  # Within last 5 minutes
            is_synthetic=True,  # Mark as synthetic data
        )
        vessels.append(vessel)

    return vessels


@router.get("/list-vessels", response_model=ListVesselsResponse)
async def list_vessels(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    ship_types: Optional[str] = Query(None, description="Comma-separated ship types"),
    limit: int = Query(1000, le=10000),
    save_positions: bool = Query(True, description="Save positions to history for route tracking"),
):
    """List AIS vessel positions within a bounding box.

    When USE_SYNTHETIC_MARITIME_DATA=True, returns demo data with:
    - data_source="synthetic" in response
    - MMSI prefix "999" on all vessels
    - is_synthetic=True on each vessel

    Positions are saved to the database for route tracking (unless save_positions=false).
    """
    cache_key = f"vessels:{min_lat}:{max_lat}:{min_lon}:{max_lon}"

    cached = await cache_get(cache_key)
    if cached:
        return ListVesselsResponse(**cached)

    # Check if using synthetic data or real data source
    if USE_SYNTHETIC_MARITIME_DATA:
        all_vessels = _generate_synthetic_vessels()
        data_source = "synthetic"
    else:
        # TODO: Query real AIS data from Delta Lake or external API
        all_vessels = []
        data_source = "real"

    # Save positions to database for route tracking
    if save_positions and all_vessels and not db.is_demo_mode:
        positions_to_save = [
            {
                "mmsi": v.mmsi,
                "name": v.name,
                "ship_type": v.ship_type,
                "flag_country": v.flag_country,
                "latitude": v.position.latitude,
                "longitude": v.position.longitude,
                "speed": v.speed,
                "course": v.course,
                "heading": v.heading,
                "destination": v.destination,
                "is_synthetic": v.is_synthetic,
            }
            for v in all_vessels
        ]
        saved_count = await save_vessel_positions_batch(positions_to_save)
        if saved_count > 0:
            print(f"[maritime] Saved {saved_count} vessel positions to history")

    # Filter by bounding box if specified
    filtered_vessels = all_vessels
    if all([min_lat is not None, max_lat is not None, min_lon is not None, max_lon is not None]):
        filtered_vessels = [
            v for v in all_vessels
            if min_lat <= v.position.latitude <= max_lat
            and min_lon <= v.position.longitude <= max_lon
        ]

    # Filter by ship types if specified
    if ship_types:
        type_list = [int(t.strip()) for t in ship_types.split(",") if t.strip().isdigit()]
        if type_list:
            filtered_vessels = [v for v in filtered_vessels if v.ship_type in type_list]

    # Apply limit
    filtered_vessels = filtered_vessels[:limit]

    now = int(datetime.utcnow().timestamp() * 1000)
    result = {
        "vessels": [v.model_dump() for v in filtered_vessels],
        "total": len(filtered_vessels),
        "updated_at": now,
        "data_source": data_source,
    }

    await cache_set(cache_key, result, 60)  # 1 minute cache
    return ListVesselsResponse(**result)


@router.get("/vessel/{mmsi}", response_model=Vessel)
async def get_vessel(mmsi: str):
    """Get details for a specific vessel by MMSI."""
    cache_key = f"vessel:{mmsi}"

    cached = await cache_get(cache_key)
    if cached:
        return Vessel(**cached)

    # Demo mode - return placeholder
    now = int(datetime.utcnow().timestamp() * 1000)
    vessel = Vessel(
        mmsi=mmsi,
        name="Unknown Vessel",
        ship_type=0,
        position=Position(latitude=0, longitude=0),
        timestamp=now,
    )

    return vessel


@router.get("/snapshot", response_model=VesselSnapshot)
async def get_vessel_snapshot():
    """Get a snapshot of all tracked vessels.

    When USE_SYNTHETIC_MARITIME_DATA=True, returns demo data with:
    - data_source="synthetic" in response
    - MMSI prefix "999" on all vessels
    - is_synthetic=True on each vessel
    """
    cache_key = "vessels:snapshot"

    cached = await cache_get(cache_key)
    if cached:
        return VesselSnapshot(**cached)

    # Check if using synthetic data or real data source
    if USE_SYNTHETIC_MARITIME_DATA:
        vessels = _generate_synthetic_vessels()
        data_source = "synthetic"
    else:
        # TODO: Query real AIS data from Delta Lake or external API
        vessels = []
        data_source = "real"

    now = int(datetime.utcnow().timestamp() * 1000)
    result = {
        "vessels": [v.model_dump() for v in vessels],
        "bounding_box": {
            "min_lat": -60,
            "max_lat": 70,
            "min_lon": -180,
            "max_lon": 180
        },
        "timestamp": now,
        "data_source": data_source,
    }

    await cache_set(cache_key, result, 30)  # 30 second cache
    return VesselSnapshot(**result)


@router.get("/vessel/{mmsi}/route", response_model=VesselRoute)
async def get_vessel_route_endpoint(
    mmsi: str,
    hours: int = Query(24, ge=1, le=720, description="Hours of history to retrieve (max 30 days)"),
):
    """Get position history/route for a specific vessel.

    Returns position history within the specified time range for route visualization.
    """
    route_data = await get_vessel_route(mmsi, hours)

    # Get vessel name from most recent position
    name = route_data[0]["name"] if route_data else None

    route_points = [
        RoutePoint(
            latitude=p["latitude"],
            longitude=p["longitude"],
            speed=p["speed"],
            course=p["course"],
            recorded_at=p["recorded_at"],
        )
        for p in route_data
    ]

    return VesselRoute(
        mmsi=mmsi,
        name=name,
        route=route_points,
        total_points=len(route_points),
    )


@router.get("/routes", response_model=VesselRoutesResponse)
async def get_all_routes(
    hours: int = Query(24, ge=1, le=720, description="Hours of history to retrieve (max 30 days)"),
):
    """Get position history for all tracked vessels.

    Returns routes for all vessels within the specified time range,
    grouped by MMSI for efficient map rendering.
    """
    routes_data = await get_all_vessel_routes(hours)

    routes = {
        mmsi: [
            RoutePoint(
                latitude=p["latitude"],
                longitude=p["longitude"],
                speed=p["speed"],
                course=p["course"],
                recorded_at=p["recorded_at"],
            )
            for p in points
        ]
        for mmsi, points in routes_data.items()
    }

    return VesselRoutesResponse(
        routes=routes,
        time_range_hours=hours,
        total_vessels=len(routes),
    )


class GenerateHistoryResponse(BaseModel):
    status: str
    message: str
    vessels_processed: int
    total_positions: int


@router.post("/admin/generate-history", response_model=GenerateHistoryResponse)
async def generate_vessel_history(
    days: int = Query(30, ge=1, le=30, description="Days of history to generate"),
    interval_hours: float = Query(4, ge=1, le=24, description="Hours between position records"),
):
    """Generate historical vessel position data for demo purposes.

    This endpoint creates synthetic route history for all demo vessels,
    enabling route visualization on the map.

    WARNING: This will add data to the database. Only run once or clear
    existing data first.
    """
    if db.is_demo_mode:
        return GenerateHistoryResponse(
            status="error",
            message="Database not available (demo mode)",
            vessels_processed=0,
            total_positions=0,
        )

    from ..scripts.generate_vessel_history import generate_vessel_route

    total_positions = 0
    vessels_processed = 0

    for idx, vessel in enumerate(SYNTHETIC_VESSELS):
        synthetic_mmsi = f"999{idx:06d}"

        # Generate route history
        positions = generate_vessel_route(
            current_lat=vessel["lat"],
            current_lon=vessel["lon"],
            destination=vessel["dest"],
            speed_kts=vessel["speed"],
            days=days,
            interval_hours=interval_hours,
        )

        if positions:
            try:
                positions_to_save = [
                    {
                        "mmsi": synthetic_mmsi,
                        "name": f"{vessel['name']} [DEMO]",
                        "ship_type": vessel["ship_type"],
                        "flag_country": vessel["flag"],
                        "latitude": p["latitude"],
                        "longitude": p["longitude"],
                        "speed": p["speed"],
                        "course": p["course"],
                        "heading": int(p["course"]),
                        "destination": vessel["dest"],
                        "is_synthetic": True,
                    }
                    for p in positions
                ]

                # Save using batch function (but we need recorded_at, so use direct insert)
                async with db.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO vessel_positions
                        (mmsi, name, ship_type, flag_country, latitude, longitude,
                         speed, course, heading, destination, is_synthetic, recorded_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        """,
                        [
                            (
                                synthetic_mmsi,
                                f"{vessel['name']} [DEMO]",
                                vessel["ship_type"],
                                vessel["flag"],
                                p["latitude"],
                                p["longitude"],
                                p["speed"],
                                p["course"],
                                int(p["course"]),
                                vessel["dest"],
                                True,
                                p["recorded_at"],
                            )
                            for p in positions
                        ]
                    )
                total_positions += len(positions)
                vessels_processed += 1
            except Exception as e:
                print(f"[maritime] Error generating history for {vessel['name']}: {e}")

    return GenerateHistoryResponse(
        status="success",
        message=f"Generated {days} days of history with {interval_hours}h intervals",
        vessels_processed=vessels_processed,
        total_positions=total_positions,
    )


class ClearHistoryResponse(BaseModel):
    status: str
    message: str
    deleted_count: int


@router.delete("/admin/clear-history", response_model=ClearHistoryResponse)
async def clear_vessel_history(
    synthetic_only: bool = Query(True, description="Only clear synthetic vessel data"),
):
    """Clear vessel position history from the database.

    Use this before regenerating historical data to avoid duplicates.
    """
    if db.is_demo_mode:
        return ClearHistoryResponse(
            status="error",
            message="Database not available (demo mode)",
            deleted_count=0,
        )

    try:
        if synthetic_only:
            result = await db.execute(
                "DELETE FROM vessel_positions WHERE is_synthetic = TRUE"
            )
        else:
            result = await db.execute("DELETE FROM vessel_positions")

        # Parse "DELETE N" response
        deleted = int(result.split()[-1]) if result else 0

        return ClearHistoryResponse(
            status="success",
            message=f"Cleared {'synthetic' if synthetic_only else 'all'} position history",
            deleted_count=deleted,
        )
    except Exception as e:
        return ClearHistoryResponse(
            status="error",
            message=str(e),
            deleted_count=0,
        )
