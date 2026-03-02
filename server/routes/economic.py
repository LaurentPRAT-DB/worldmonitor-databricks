"""
Economic API endpoints - FRED and World Bank data.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..config import settings
from ..db import cache_get, cache_set

router = APIRouter()


class DataPoint(BaseModel):
    date: str
    value: float


class FredSeries(BaseModel):
    series_id: str
    title: str
    units: str
    frequency: str
    data: list[DataPoint]
    last_updated: str


class WorldBankIndicator(BaseModel):
    indicator_id: str
    indicator_name: str
    country: str
    country_code: str
    data: list[DataPoint]


class ListWorldBankIndicatorsResponse(BaseModel):
    indicators: list[WorldBankIndicator]
    total: int


class MacroSignal(BaseModel):
    name: str
    value: float
    change: float
    trend: str  # up, down, flat
    unit: str


class MacroSignalsResponse(BaseModel):
    signals: list[MacroSignal]
    updated_at: int


# FRED API
FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_CACHE_TTL = 3600  # 1 hour

# World Bank API
WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"
WORLD_BANK_CACHE_TTL = 86400  # 24 hours


@router.get("/get-fred-series/{series_id}", response_model=FredSeries)
async def get_fred_series(
    series_id: str,
    limit: int = Query(100, le=1000),
):
    """Get FRED economic data series."""
    cache_key = f"fred:{series_id}:{limit}"

    cached = await cache_get(cache_key)
    if cached:
        return FredSeries(**cached)

    series = FredSeries(
        series_id=series_id,
        title=series_id,
        units="",
        frequency="",
        data=[],
        last_updated=datetime.utcnow().isoformat(),
    )

    if settings.FRED_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get series info
                info_response = await client.get(
                    f"{FRED_BASE_URL}/series",
                    params={
                        "series_id": series_id,
                        "api_key": settings.FRED_API_KEY,
                        "file_type": "json",
                    }
                )
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    if info_data.get("seriess"):
                        s = info_data["seriess"][0]
                        series.title = s.get("title", series_id)
                        series.units = s.get("units", "")
                        series.frequency = s.get("frequency", "")

                # Get observations
                obs_response = await client.get(
                    f"{FRED_BASE_URL}/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": settings.FRED_API_KEY,
                        "file_type": "json",
                        "limit": limit,
                        "sort_order": "desc",
                    }
                )
                if obs_response.status_code == 200:
                    obs_data = obs_response.json()
                    for obs in obs_data.get("observations", []):
                        try:
                            value = float(obs.get("value", 0))
                            series.data.append(DataPoint(
                                date=obs.get("date", ""),
                                value=value,
                            ))
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            print(f"[fred] API error: {e}")

    result = series.model_dump()
    await cache_set(cache_key, result, FRED_CACHE_TTL)
    return series


@router.get("/list-world-bank-indicators", response_model=ListWorldBankIndicatorsResponse)
async def list_world_bank_indicators(
    indicator: str = Query("NY.GDP.MKTP.CD", description="Indicator ID"),
    countries: str = Query("US,CN,DE,JP,GB", description="Comma-separated country codes"),
    years: int = Query(10, ge=1, le=50, description="Years of data"),
):
    """Get World Bank development indicators."""
    cache_key = f"worldbank:{indicator}:{countries}:{years}"

    cached = await cache_get(cache_key)
    if cached:
        return ListWorldBankIndicatorsResponse(**cached)

    indicators = []
    current_year = datetime.utcnow().year

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            country_list = countries.replace(",", ";")
            start_year = current_year - years

            response = await client.get(
                f"{WORLD_BANK_BASE_URL}/country/{country_list}/indicator/{indicator}",
                params={
                    "format": "json",
                    "date": f"{start_year}:{current_year}",
                    "per_page": 500,
                }
            )

            if response.status_code == 200:
                data = response.json()
                if len(data) > 1 and data[1]:
                    # Group by country
                    country_data = {}
                    for item in data[1]:
                        country_code = item.get("country", {}).get("id", "")
                        country_name = item.get("country", {}).get("value", "")
                        indicator_name = item.get("indicator", {}).get("value", "")

                        if country_code not in country_data:
                            country_data[country_code] = {
                                "country": country_name,
                                "indicator_name": indicator_name,
                                "data": [],
                            }

                        value = item.get("value")
                        if value is not None:
                            country_data[country_code]["data"].append(DataPoint(
                                date=item.get("date", ""),
                                value=float(value),
                            ))

                    for code, info in country_data.items():
                        indicators.append(WorldBankIndicator(
                            indicator_id=indicator,
                            indicator_name=info["indicator_name"],
                            country=info["country"],
                            country_code=code,
                            data=sorted(info["data"], key=lambda x: x.date, reverse=True),
                        ))
    except Exception as e:
        print(f"[worldbank] API error: {e}")

    result = {
        "indicators": [i.model_dump() for i in indicators],
        "total": len(indicators)
    }
    await cache_set(cache_key, result, WORLD_BANK_CACHE_TTL)
    return ListWorldBankIndicatorsResponse(**result)


@router.get("/macro-signals", response_model=MacroSignalsResponse)
async def get_macro_signals():
    """Get macro economic signals summary."""
    cache_key = "macro:signals"

    cached = await cache_get(cache_key)
    if cached:
        return MacroSignalsResponse(**cached)

    # Key FRED series for macro signals
    key_series = [
        ("DGS10", "10-Year Treasury", "%"),
        ("FEDFUNDS", "Fed Funds Rate", "%"),
        ("UNRATE", "Unemployment", "%"),
        ("CPIAUCSL", "CPI Index", "Index"),
        ("GDPC1", "Real GDP", "B$"),
    ]

    signals = []
    for series_id, name, unit in key_series:
        try:
            series = await get_fred_series(series_id, limit=2)
            if series.data:
                current = series.data[0].value
                previous = series.data[1].value if len(series.data) > 1 else current
                change = current - previous
                trend = "up" if change > 0 else "down" if change < 0 else "flat"

                signals.append(MacroSignal(
                    name=name,
                    value=round(current, 2),
                    change=round(change, 2),
                    trend=trend,
                    unit=unit,
                ))
        except Exception:
            continue

    result = {
        "signals": [s.model_dump() for s in signals],
        "updated_at": int(datetime.utcnow().timestamp() * 1000)
    }
    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return MacroSignalsResponse(**result)
