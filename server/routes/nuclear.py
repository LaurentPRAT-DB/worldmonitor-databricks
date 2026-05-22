"""
Nuclear Facilities API endpoints - Global nuclear infrastructure monitoring.
"""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import cache_get, cache_set

router = APIRouter()


class Position(BaseModel):
    latitude: float
    longitude: float


class NuclearFacility(BaseModel):
    id: str
    name: str
    country: str
    position: Position
    facility_type: str  # power_plant, research, enrichment, reprocessing, storage
    status: str  # operational, under_construction, decommissioned, shutdown, conflict_zone
    capacity_mw: Optional[float] = None
    operator: Optional[str] = None
    year_commissioned: Optional[int] = None


class ListNuclearFacilitiesResponse(BaseModel):
    facilities: list[NuclearFacility]
    total: int


NUCLEAR_FACILITIES = [
    # Ukraine — Conflict Zone
    {
        "id": "nuc-zaporizhzhia",
        "name": "Zaporizhzhia Nuclear Power Plant",
        "country": "Ukraine",
        "position": {"latitude": 47.5069, "longitude": 34.5853},
        "facility_type": "power_plant",
        "status": "conflict_zone",
        "capacity_mw": 5700,
        "operator": "Energoatom (occupied)",
        "year_commissioned": 1984,
    },
    {
        "id": "nuc-chernobyl",
        "name": "Chernobyl Exclusion Zone",
        "country": "Ukraine",
        "position": {"latitude": 51.3891, "longitude": 30.0980},
        "facility_type": "storage",
        "status": "decommissioned",
        "capacity_mw": None,
        "operator": "State Agency of Ukraine",
        "year_commissioned": 1977,
    },
    # Iran
    {
        "id": "nuc-bushehr",
        "name": "Bushehr Nuclear Power Plant",
        "country": "Iran",
        "position": {"latitude": 28.8314, "longitude": 50.8868},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 1000,
        "operator": "AEOI",
        "year_commissioned": 2011,
    },
    {
        "id": "nuc-natanz",
        "name": "Natanz Enrichment Facility",
        "country": "Iran",
        "position": {"latitude": 33.7214, "longitude": 51.7275},
        "facility_type": "enrichment",
        "status": "operational",
        "capacity_mw": None,
        "operator": "AEOI",
        "year_commissioned": 2007,
    },
    {
        "id": "nuc-fordow",
        "name": "Fordow Fuel Enrichment Plant",
        "country": "Iran",
        "position": {"latitude": 34.8808, "longitude": 51.5842},
        "facility_type": "enrichment",
        "status": "operational",
        "capacity_mw": None,
        "operator": "AEOI",
        "year_commissioned": 2012,
    },
    # Israel
    {
        "id": "nuc-dimona",
        "name": "Negev Nuclear Research Center (Dimona)",
        "country": "Israel",
        "position": {"latitude": 31.0014, "longitude": 35.1447},
        "facility_type": "research",
        "status": "operational",
        "capacity_mw": None,
        "operator": "IAEC",
        "year_commissioned": 1963,
    },
    # Japan
    {
        "id": "nuc-fukushima",
        "name": "Fukushima Daiichi",
        "country": "Japan",
        "position": {"latitude": 37.4211, "longitude": 141.0328},
        "facility_type": "power_plant",
        "status": "decommissioned",
        "capacity_mw": 4696,
        "operator": "TEPCO",
        "year_commissioned": 1971,
    },
    {
        "id": "nuc-kashiwazaki",
        "name": "Kashiwazaki-Kariwa",
        "country": "Japan",
        "position": {"latitude": 37.4264, "longitude": 138.5978},
        "facility_type": "power_plant",
        "status": "shutdown",
        "capacity_mw": 7965,
        "operator": "TEPCO",
        "year_commissioned": 1985,
    },
    # France
    {
        "id": "nuc-la-hague",
        "name": "La Hague Reprocessing Plant",
        "country": "France",
        "position": {"latitude": 49.6783, "longitude": -1.8817},
        "facility_type": "reprocessing",
        "status": "operational",
        "capacity_mw": None,
        "operator": "Orano",
        "year_commissioned": 1976,
    },
    {
        "id": "nuc-gravelines",
        "name": "Gravelines Nuclear Power Plant",
        "country": "France",
        "position": {"latitude": 51.0153, "longitude": 2.1069},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 5460,
        "operator": "EDF",
        "year_commissioned": 1980,
    },
    # UK
    {
        "id": "nuc-sellafield",
        "name": "Sellafield Reprocessing Complex",
        "country": "United Kingdom",
        "position": {"latitude": 54.4203, "longitude": -3.4981},
        "facility_type": "reprocessing",
        "status": "decommissioned",
        "capacity_mw": None,
        "operator": "Sellafield Ltd",
        "year_commissioned": 1956,
    },
    {
        "id": "nuc-hinkley-c",
        "name": "Hinkley Point C",
        "country": "United Kingdom",
        "position": {"latitude": 51.2084, "longitude": -3.1306},
        "facility_type": "power_plant",
        "status": "under_construction",
        "capacity_mw": 3260,
        "operator": "EDF Energy",
        "year_commissioned": None,
    },
    # USA
    {
        "id": "nuc-three-mile",
        "name": "Three Mile Island",
        "country": "United States",
        "position": {"latitude": 40.1531, "longitude": -76.7247},
        "facility_type": "power_plant",
        "status": "shutdown",
        "capacity_mw": 819,
        "operator": "Constellation Energy",
        "year_commissioned": 1974,
    },
    {
        "id": "nuc-palo-verde",
        "name": "Palo Verde Generating Station",
        "country": "United States",
        "position": {"latitude": 33.3881, "longitude": -112.8617},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 3937,
        "operator": "Arizona Public Service",
        "year_commissioned": 1986,
    },
    {
        "id": "nuc-vogtle",
        "name": "Vogtle Electric Generating Plant",
        "country": "United States",
        "position": {"latitude": 33.1417, "longitude": -81.7631},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 4540,
        "operator": "Southern Nuclear",
        "year_commissioned": 1987,
    },
    # Russia
    {
        "id": "nuc-kursk",
        "name": "Kursk Nuclear Power Plant",
        "country": "Russia",
        "position": {"latitude": 51.6711, "longitude": 35.6064},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 4000,
        "operator": "Rosenergoatom",
        "year_commissioned": 1976,
    },
    {
        "id": "nuc-mayak",
        "name": "Mayak Nuclear Complex",
        "country": "Russia",
        "position": {"latitude": 55.7139, "longitude": 60.8050},
        "facility_type": "reprocessing",
        "status": "operational",
        "capacity_mw": None,
        "operator": "Rosatom",
        "year_commissioned": 1948,
    },
    # China
    {
        "id": "nuc-taishan",
        "name": "Taishan Nuclear Power Plant",
        "country": "China",
        "position": {"latitude": 21.9106, "longitude": 112.9811},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 3400,
        "operator": "CGN/EDF",
        "year_commissioned": 2018,
    },
    {
        "id": "nuc-daya-bay",
        "name": "Daya Bay Nuclear Power Plant",
        "country": "China",
        "position": {"latitude": 22.5969, "longitude": 114.5439},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 1968,
        "operator": "CGN",
        "year_commissioned": 1994,
    },
    # India
    {
        "id": "nuc-kudankulam",
        "name": "Kudankulam Nuclear Power Plant",
        "country": "India",
        "position": {"latitude": 8.1681, "longitude": 77.7089},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 2000,
        "operator": "NPCIL",
        "year_commissioned": 2013,
    },
    # Pakistan
    {
        "id": "nuc-karachi",
        "name": "Karachi Nuclear Power Complex",
        "country": "Pakistan",
        "position": {"latitude": 24.8422, "longitude": 66.7839},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 2200,
        "operator": "PAEC",
        "year_commissioned": 2021,
    },
    # North Korea
    {
        "id": "nuc-yongbyon",
        "name": "Yongbyon Nuclear Scientific Research Center",
        "country": "North Korea",
        "position": {"latitude": 39.7953, "longitude": 125.7550},
        "facility_type": "research",
        "status": "operational",
        "capacity_mw": None,
        "operator": "DPRK",
        "year_commissioned": 1986,
    },
    # South Korea
    {
        "id": "nuc-kori",
        "name": "Shin Kori Nuclear Power Plant",
        "country": "South Korea",
        "position": {"latitude": 35.3200, "longitude": 129.2831},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 5600,
        "operator": "KHNP",
        "year_commissioned": 2010,
    },
    # Taiwan
    {
        "id": "nuc-lungmen",
        "name": "Lungmen Nuclear Power Plant",
        "country": "Taiwan",
        "position": {"latitude": 25.0231, "longitude": 121.9194},
        "facility_type": "power_plant",
        "status": "shutdown",
        "capacity_mw": 2700,
        "operator": "Taipower",
        "year_commissioned": None,
    },
    # Brazil
    {
        "id": "nuc-angra",
        "name": "Angra Nuclear Power Plant",
        "country": "Brazil",
        "position": {"latitude": -23.0083, "longitude": -44.4572},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 1990,
        "operator": "Eletronuclear",
        "year_commissioned": 1985,
    },
    # UAE
    {
        "id": "nuc-barakah",
        "name": "Barakah Nuclear Power Plant",
        "country": "United Arab Emirates",
        "position": {"latitude": 23.9589, "longitude": 52.2594},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 5600,
        "operator": "ENEC/Nawah",
        "year_commissioned": 2020,
    },
    # Saudi Arabia
    {
        "id": "nuc-saudi-research",
        "name": "King Abdulaziz City for Science (reactor)",
        "country": "Saudi Arabia",
        "position": {"latitude": 24.6275, "longitude": 46.7114},
        "facility_type": "research",
        "status": "operational",
        "capacity_mw": None,
        "operator": "KACST",
        "year_commissioned": 2019,
    },
    # South Africa
    {
        "id": "nuc-koeberg",
        "name": "Koeberg Nuclear Power Station",
        "country": "South Africa",
        "position": {"latitude": -33.6764, "longitude": 18.4353},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 1860,
        "operator": "Eskom",
        "year_commissioned": 1984,
    },
    # Canada
    {
        "id": "nuc-bruce",
        "name": "Bruce Nuclear Generating Station",
        "country": "Canada",
        "position": {"latitude": 44.3253, "longitude": -81.6000},
        "facility_type": "power_plant",
        "status": "operational",
        "capacity_mw": 6384,
        "operator": "Bruce Power",
        "year_commissioned": 1977,
    },
]


@router.get("/list-nuclear-facilities", response_model=ListNuclearFacilitiesResponse)
async def list_nuclear_facilities(
    country: Optional[str] = Query(None, description="Filter by country"),
    status: Optional[str] = Query(None, description="Filter by status"),
    facility_type: Optional[str] = Query(None, description="Filter by facility type"),
):
    """
    List global nuclear facilities including power plants, enrichment,
    reprocessing, research, and storage sites.
    """
    cache_key = f"nuclear:{country or 'all'}:{status or 'all'}:{facility_type or 'all'}"

    cached = await cache_get(cache_key)
    if cached:
        return ListNuclearFacilitiesResponse(**cached)

    filtered = NUCLEAR_FACILITIES

    if country:
        filtered = [f for f in filtered if f["country"].lower() == country.lower()]
    if status:
        filtered = [f for f in filtered if f["status"] == status]
    if facility_type:
        filtered = [f for f in filtered if f["facility_type"] == facility_type]

    result = {"facilities": filtered, "total": len(filtered)}
    await cache_set(cache_key, result, 3600)  # 1 hour cache (static data)
    return ListNuclearFacilitiesResponse(**result)
