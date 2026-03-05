"""
Military API endpoints - Flight tracking, bases, fleet reports.

Synthetic data based on typical Middle East/Persian Gulf military activity patterns.
Focus areas: Strait of Hormuz, Iranian airspace, US 5th Fleet operations.
"""

import random
from typing import Optional
from datetime import datetime, timedelta
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
    aircraft_type: Optional[str] = None
    mission_type: Optional[str] = None
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
    status: str = "active"  # active, heightened, exercise


class ListMilitaryBasesResponse(BaseModel):
    bases: list[MilitaryBase]
    total: int


class TheaterPosture(BaseModel):
    theater: str
    alert_level: str  # low, elevated, high, critical
    active_flights: int
    recent_incidents: int
    assessment: str


# ============================================================================
# SYNTHETIC DATA: Military Bases (Real locations)
# ============================================================================

MILITARY_BASES = [
    # US/Coalition Bases - Persian Gulf
    {
        "id": "base-al-udeid",
        "name": "Al Udeid Air Base",
        "country": "Qatar",
        "position": {"latitude": 25.1173, "longitude": 51.3150, "altitude": 40},
        "base_type": "air",
        "operator": "US Air Force / Qatar Air Force",
        "status": "heightened",
    },
    {
        "id": "base-nsa-bahrain",
        "name": "Naval Support Activity Bahrain",
        "country": "Bahrain",
        "position": {"latitude": 26.2361, "longitude": 50.6503, "altitude": 5},
        "base_type": "naval",
        "operator": "US Navy 5th Fleet",
        "status": "heightened",
    },
    {
        "id": "base-al-dhafra",
        "name": "Al Dhafra Air Base",
        "country": "United Arab Emirates",
        "position": {"latitude": 24.2481, "longitude": 54.5472, "altitude": 23},
        "base_type": "air",
        "operator": "US Air Force / UAE Air Force",
        "status": "active",
    },
    {
        "id": "base-camp-arifjan",
        "name": "Camp Arifjan",
        "country": "Kuwait",
        "position": {"latitude": 28.9333, "longitude": 48.1000, "altitude": 40},
        "base_type": "army",
        "operator": "US Army Central",
        "status": "active",
    },
    {
        "id": "base-prince-sultan",
        "name": "Prince Sultan Air Base",
        "country": "Saudi Arabia",
        "position": {"latitude": 24.0625, "longitude": 47.5806, "altitude": 505},
        "base_type": "air",
        "operator": "US Air Force / Royal Saudi Air Force",
        "status": "active",
    },
    # Iranian Military Bases
    {
        "id": "base-bandar-abbas",
        "name": "Bandar Abbas Naval Base",
        "country": "Iran",
        "position": {"latitude": 27.1832, "longitude": 56.2666, "altitude": 10},
        "base_type": "naval",
        "operator": "Islamic Republic of Iran Navy",
        "status": "heightened",
    },
    {
        "id": "base-bushehr",
        "name": "Bushehr Air Base",
        "country": "Iran",
        "position": {"latitude": 28.9181, "longitude": 50.8344, "altitude": 20},
        "base_type": "air",
        "operator": "Islamic Republic of Iran Air Force",
        "status": "heightened",
    },
    {
        "id": "base-chabahar",
        "name": "Chabahar Naval Base",
        "country": "Iran",
        "position": {"latitude": 25.2919, "longitude": 60.6430, "altitude": 8},
        "base_type": "naval",
        "operator": "IRGC Navy",
        "status": "active",
    },
    {
        "id": "base-konarak",
        "name": "Konarak Naval Base",
        "country": "Iran",
        "position": {"latitude": 25.3500, "longitude": 60.3833, "altitude": 5},
        "base_type": "naval",
        "operator": "IRGC Navy",
        "status": "heightened",
    },
    {
        "id": "base-jask",
        "name": "Jask Forward Operating Base",
        "country": "Iran",
        "position": {"latitude": 25.6386, "longitude": 57.7703, "altitude": 15},
        "base_type": "naval",
        "operator": "IRGC Navy",
        "status": "heightened",
    },
    {
        "id": "base-tactical-isfahan",
        "name": "Isfahan Air Base (8th TFB)",
        "country": "Iran",
        "position": {"latitude": 32.7508, "longitude": 51.8614, "altitude": 1600},
        "base_type": "air",
        "operator": "IRIAF",
        "status": "active",
    },
    # Other Regional
    {
        "id": "base-diego-garcia",
        "name": "Naval Support Facility Diego Garcia",
        "country": "British Indian Ocean Territory",
        "position": {"latitude": -7.3133, "longitude": 72.4111, "altitude": 3},
        "base_type": "joint",
        "operator": "US Navy / Royal Navy",
        "status": "active",
    },
    {
        "id": "base-djibouti",
        "name": "Camp Lemonnier",
        "country": "Djibouti",
        "position": {"latitude": 11.5469, "longitude": 43.1556, "altitude": 15},
        "base_type": "joint",
        "operator": "US Africa Command",
        "status": "active",
    },
    {
        "id": "base-oman-masirah",
        "name": "Masirah Air Base",
        "country": "Oman",
        "position": {"latitude": 20.6754, "longitude": 58.8905, "altitude": 19},
        "base_type": "air",
        "operator": "Royal Air Force of Oman",
        "status": "active",
    },
]


# ============================================================================
# SYNTHETIC DATA: Flight Templates (Realistic patterns)
# ============================================================================

FLIGHT_TEMPLATES = [
    # US Navy Patrol - P-8 Poseidon (Maritime surveillance)
    {
        "callsign_prefix": "NAVY",
        "origin_country": "United States",
        "classification": "military",
        "aircraft_type": "P-8A Poseidon",
        "mission_type": "Maritime Patrol",
        "base_lat": 26.24, "base_lon": 50.65,  # Bahrain
        "patrol_area": {"lat_min": 25.5, "lat_max": 27.5, "lon_min": 54.0, "lon_max": 57.0},
        "altitude_range": (5000, 8000),
        "speed_range": (400, 480),
    },
    # US Air Force - RC-135 (SIGINT)
    {
        "callsign_prefix": "COBRA",
        "origin_country": "United States",
        "classification": "military",
        "aircraft_type": "RC-135V/W Rivet Joint",
        "mission_type": "SIGINT/ELINT",
        "base_lat": 25.12, "base_lon": 51.32,  # Al Udeid
        "patrol_area": {"lat_min": 24.0, "lat_max": 28.0, "lon_min": 52.0, "lon_max": 58.0},
        "altitude_range": (28000, 35000),
        "speed_range": (450, 520),
    },
    # US MQ-9 Reaper Drone
    {
        "callsign_prefix": "REAPER",
        "origin_country": "United States",
        "classification": "military",
        "aircraft_type": "MQ-9 Reaper",
        "mission_type": "ISR",
        "base_lat": 24.25, "base_lon": 54.55,  # Al Dhafra
        "patrol_area": {"lat_min": 25.0, "lat_max": 27.0, "lon_min": 55.0, "lon_max": 58.0},
        "altitude_range": (18000, 25000),
        "speed_range": (180, 240),
    },
    # Iranian F-14 Tomcat (Yes, they still fly them)
    {
        "callsign_prefix": "IRIAF",
        "origin_country": "Iran",
        "classification": "military",
        "aircraft_type": "F-14A Tomcat",
        "mission_type": "Air Defense Patrol",
        "base_lat": 28.92, "base_lon": 50.83,  # Bushehr
        "patrol_area": {"lat_min": 26.0, "lat_max": 28.5, "lon_min": 51.0, "lon_max": 54.0},
        "altitude_range": (20000, 35000),
        "speed_range": (400, 600),
    },
    # Iranian Su-35 (Recent acquisition)
    {
        "callsign_prefix": "IRIAF",
        "origin_country": "Iran",
        "classification": "military",
        "aircraft_type": "Su-35S Flanker-E",
        "mission_type": "Combat Air Patrol",
        "base_lat": 32.75, "base_lon": 51.86,  # Isfahan
        "patrol_area": {"lat_min": 26.5, "lat_max": 29.0, "lon_min": 52.0, "lon_max": 56.0},
        "altitude_range": (25000, 40000),
        "speed_range": (500, 700),
    },
    # IRGC Shahed-136 Drone (Hormuz patrol)
    {
        "callsign_prefix": "IRGC",
        "origin_country": "Iran",
        "classification": "military",
        "aircraft_type": "Shahed-136",
        "mission_type": "Maritime Surveillance",
        "base_lat": 25.64, "base_lon": 57.77,  # Jask
        "patrol_area": {"lat_min": 25.0, "lat_max": 26.8, "lon_min": 56.0, "lon_max": 58.5},
        "altitude_range": (2000, 8000),
        "speed_range": (150, 200),
    },
    # IRGC Fast Boat Support Helo
    {
        "callsign_prefix": "SEPAH",
        "origin_country": "Iran",
        "classification": "military",
        "aircraft_type": "Bell 212/214",
        "mission_type": "Naval Support",
        "base_lat": 27.18, "base_lon": 56.27,  # Bandar Abbas
        "patrol_area": {"lat_min": 26.0, "lat_max": 27.2, "lon_min": 55.5, "lon_max": 57.0},
        "altitude_range": (500, 3000),
        "speed_range": (100, 150),
    },
    # UAE E-2D Hawkeye (AEW)
    {
        "callsign_prefix": "UAEAF",
        "origin_country": "United Arab Emirates",
        "classification": "military",
        "aircraft_type": "GlobalEye AEW&C",
        "mission_type": "Airborne Early Warning",
        "base_lat": 24.25, "base_lon": 54.55,  # Al Dhafra
        "patrol_area": {"lat_min": 23.5, "lat_max": 26.5, "lon_min": 53.0, "lon_max": 57.0},
        "altitude_range": (28000, 35000),
        "speed_range": (350, 420),
    },
    # Saudi AWACS
    {
        "callsign_prefix": "RSAF",
        "origin_country": "Saudi Arabia",
        "classification": "military",
        "aircraft_type": "E-3A Sentry AWACS",
        "mission_type": "Airborne Early Warning",
        "base_lat": 24.06, "base_lon": 47.58,  # Prince Sultan
        "patrol_area": {"lat_min": 23.0, "lat_max": 28.0, "lon_min": 45.0, "lon_max": 52.0},
        "altitude_range": (28000, 35000),
        "speed_range": (380, 450),
    },
    # RAF Typhoon (Qatar based)
    {
        "callsign_prefix": "RAFAIR",
        "origin_country": "United Kingdom",
        "classification": "military",
        "aircraft_type": "Eurofighter Typhoon FGR4",
        "mission_type": "Quick Reaction Alert",
        "base_lat": 25.12, "base_lon": 51.32,  # Al Udeid
        "patrol_area": {"lat_min": 24.0, "lat_max": 27.0, "lon_min": 50.0, "lon_max": 55.0},
        "altitude_range": (25000, 40000),
        "speed_range": (500, 800),
    },
]


def generate_synthetic_flights() -> list[dict]:
    """Generate realistic synthetic military flight data."""
    now = datetime.utcnow()
    flights = []

    for i, template in enumerate(FLIGHT_TEMPLATES):
        # Random number of this aircraft type in the air (1-3)
        num_aircraft = random.randint(1, 3) if template["origin_country"] in ["Iran", "United States"] else random.randint(0, 2)

        for j in range(num_aircraft):
            patrol = template["patrol_area"]
            lat = random.uniform(patrol["lat_min"], patrol["lat_max"])
            lon = random.uniform(patrol["lon_min"], patrol["lon_max"])
            alt = random.uniform(*template["altitude_range"])
            speed = random.uniform(*template["speed_range"])
            heading = random.uniform(0, 360)

            # Generate realistic callsign
            callsign = f"{template['callsign_prefix']}{random.randint(10, 99)}"

            # Generate ICAO24 hex code
            icao24 = f"{random.randint(0x700000, 0x7FFFFF):06x}"

            # Timestamp with some variation
            ts = now - timedelta(minutes=random.randint(0, 30))

            flights.append({
                "icao24": icao24,
                "callsign": callsign,
                "origin_country": template["origin_country"],
                "position": {
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "altitude": round(alt, 0),
                },
                "velocity": round(speed, 1),
                "heading": round(heading, 1),
                "vertical_rate": round(random.uniform(-500, 500), 0),
                "on_ground": False,
                "classification": template["classification"],
                "aircraft_type": template["aircraft_type"],
                "mission_type": template["mission_type"],
                "timestamp": int(ts.timestamp() * 1000),
            })

    return flights


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/list-military-flights", response_model=ListMilitaryFlightsResponse)
async def list_military_flights(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
):
    """
    List military/government aircraft activity.

    Synthetic data focused on Persian Gulf / Strait of Hormuz region.
    Reflects heightened Iran activity and US 5th Fleet patrols.
    """
    cache_key = f"flights:military:{min_lat}:{max_lat}:{min_lon}:{max_lon}:{countries}"

    cached = await cache_get(cache_key)
    if cached:
        return ListMilitaryFlightsResponse(**cached)

    # Generate synthetic flights
    all_flights = generate_synthetic_flights()

    # Apply filters
    filtered = all_flights

    if min_lat is not None:
        filtered = [f for f in filtered if f["position"]["latitude"] >= min_lat]
    if max_lat is not None:
        filtered = [f for f in filtered if f["position"]["latitude"] <= max_lat]
    if min_lon is not None:
        filtered = [f for f in filtered if f["position"]["longitude"] >= min_lon]
    if max_lon is not None:
        filtered = [f for f in filtered if f["position"]["longitude"] <= max_lon]

    if countries:
        country_list = [c.strip() for c in countries.split(",")]
        filtered = [f for f in filtered if f["origin_country"] in country_list]

    now = int(datetime.utcnow().timestamp() * 1000)
    result = {
        "flights": filtered,
        "total": len(filtered),
        "updated_at": now,
    }

    await cache_set(cache_key, result, 60)  # 1 minute cache (flights move fast)
    return ListMilitaryFlightsResponse(**result)


@router.get("/list-military-bases", response_model=ListMilitaryBasesResponse)
async def list_military_bases(
    country: Optional[str] = Query(None, description="Filter by country code"),
    base_type: Optional[str] = Query(None, description="Filter by base type"),
):
    """
    List known military bases in Persian Gulf and surrounding region.

    Includes US 5th Fleet facilities, Iranian naval/air bases, and coalition partners.
    """
    cache_key = f"bases:{country or 'all'}:{base_type or 'all'}"

    cached = await cache_get(cache_key)
    if cached:
        return ListMilitaryBasesResponse(**cached)

    # Filter bases
    filtered = MILITARY_BASES

    if country:
        filtered = [b for b in filtered if b["country"].lower() == country.lower()]
    if base_type:
        filtered = [b for b in filtered if b["base_type"].lower() == base_type.lower()]

    result = {"bases": filtered, "total": len(filtered)}
    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return ListMilitaryBasesResponse(**result)


@router.get("/theater-posture/{theater}", response_model=TheaterPosture)
async def get_theater_posture(theater: str):
    """
    Get posture assessment for a military theater.

    Supported theaters: persian-gulf, red-sea, mediterranean, indo-pacific
    """
    cache_key = f"posture:{theater}"

    cached = await cache_get(cache_key)
    if cached:
        return TheaterPosture(**cached)

    # Theater-specific assessments (reflecting current tensions)
    postures = {
        "persian-gulf": TheaterPosture(
            theater="Persian Gulf / Strait of Hormuz",
            alert_level="high",
            active_flights=len([t for t in FLIGHT_TEMPLATES if "patrol_area" in t]),
            recent_incidents=7,
            assessment=(
                "ELEVATED ACTIVITY: Iranian naval and air forces conducting increased "
                "patrols near Strait of Hormuz. IRGC fast boats observed harassing "
                "commercial shipping. US 5th Fleet has increased P-8 maritime patrol "
                "sorties. Multiple Iranian drone incursions reported in past 72 hours. "
                "Commercial vessels advised to maintain AIS and coordinate with UKMTO."
            ),
        ),
        "red-sea": TheaterPosture(
            theater="Red Sea / Gulf of Aden",
            alert_level="elevated",
            active_flights=4,
            recent_incidents=3,
            assessment=(
                "MODERATE ACTIVITY: Houthi drone and missile attacks on commercial "
                "shipping continue. US and allied naval forces conducting escort "
                "operations. Vessels transiting Bab el-Mandeb advised to increase "
                "vigilance and report suspicious activity."
            ),
        ),
        "mediterranean": TheaterPosture(
            theater="Eastern Mediterranean",
            alert_level="elevated",
            active_flights=6,
            recent_incidents=2,
            assessment=(
                "STABLE BUT TENSE: Russian naval presence remains significant. "
                "NATO air policing missions ongoing. Israeli Air Force conducting "
                "periodic strikes in Syria. Cyprus FIR congested with military traffic."
            ),
        ),
        "indo-pacific": TheaterPosture(
            theater="Indo-Pacific",
            alert_level="low",
            active_flights=8,
            recent_incidents=1,
            assessment=(
                "ROUTINE ACTIVITY: Standard freedom of navigation operations. "
                "Chinese military exercises in South China Sea ongoing but within "
                "normal parameters. Taiwan Strait transits proceeding normally."
            ),
        ),
    }

    posture = postures.get(
        theater.lower().replace(" ", "-"),
        TheaterPosture(
            theater=theater,
            alert_level="unknown",
            active_flights=0,
            recent_incidents=0,
            assessment="No assessment available for this theater.",
        ),
    )

    await cache_set(cache_key, posture.model_dump(), 300)  # 5 minute cache
    return posture
