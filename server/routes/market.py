"""
Market API endpoints - Stock quotes, crypto, commodities, ETFs.

STORAGE PATTERN: Lakebase-first for quote history
- Current quotes fetched from APIs and persisted to Lakebase
- Historical data available for time-based navigation
- 24-hour retention in Lakebase
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx

from ..config import settings
from ..db import (
    cache_get,
    cache_set,
    db,
    save_market_quotes_batch,
    get_market_quotes_from_lakebase,
    get_quote_history,
    RETENTION_HOURS,
)

router = APIRouter()


class Quote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    timestamp: int


class ListQuotesResponse(BaseModel):
    quotes: list[Quote]
    updated_at: int


class ETFFlow(BaseModel):
    symbol: str
    name: str
    flow_1d: float  # 1-day flow in millions
    flow_1w: float  # 1-week flow
    flow_1m: float  # 1-month flow
    aum: float  # Assets under management
    category: str


class ListETFFlowsResponse(BaseModel):
    flows: list[ETFFlow]
    updated_at: int


# Finnhub API configuration
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
MARKET_CACHE_TTL = 60  # 1 minute for real-time quotes

# Major indices and their components
MAJOR_INDICES = ["SPY", "QQQ", "DIA", "IWM", "VTI"]
COMMODITIES = ["GC=F", "SI=F", "CL=F", "NG=F"]  # Gold, Silver, Oil, Natural Gas
CRYPTO = ["BTC", "ETH", "SOL", "XRP", "ADA"]


@router.get("/list-market-quotes", response_model=ListQuotesResponse)
async def list_market_quotes(
    symbols: str = Query(",".join(MAJOR_INDICES), description="Comma-separated symbols"),
):
    """Get real-time quotes for market indices/stocks.

    LAKEBASE-FIRST PATTERN:
    - Quotes are fetched from Finnhub and persisted to Lakebase
    - Enables historical price tracking for time-based navigation
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    cache_key = f"quotes:{','.join(sorted(symbol_list))}"

    cached = await cache_get(cache_key)
    if cached:
        return ListQuotesResponse(**cached)

    quotes = []
    quotes_to_persist = []
    now = int(datetime.utcnow().timestamp() * 1000)

    if settings.FINNHUB_API_KEY:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for symbol in symbol_list[:20]:  # Limit to 20 symbols
                try:
                    response = await client.get(
                        f"{FINNHUB_BASE_URL}/quote",
                        params={"symbol": symbol, "token": settings.FINNHUB_API_KEY}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("c"):  # Current price exists
                            quote = Quote(
                                symbol=symbol,
                                name=symbol,  # Would need another API call for name
                                price=float(data.get("c", 0)),
                                change=float(data.get("d", 0) or 0),
                                change_percent=float(data.get("dp", 0) or 0),
                                volume=None,
                                market_cap=None,
                                timestamp=now,
                            )
                            quotes.append(quote)

                            # Prepare for Lakebase persistence
                            quotes_to_persist.append({
                                "symbol": symbol,
                                "asset_type": "stock",
                                "name": symbol,
                                "price": quote.price,
                                "change": quote.change,
                                "change_percent": quote.change_percent,
                                "volume": None,
                                "market_cap": None,
                            })
                except Exception as e:
                    print(f"[finnhub] Error fetching {symbol}: {e}")
    else:
        # Demo mode - return placeholder data
        for symbol in symbol_list[:20]:
            quotes.append(Quote(
                symbol=symbol,
                name=symbol,
                price=100.0,
                change=0.0,
                change_percent=0.0,
                volume=None,
                market_cap=None,
                timestamp=now,
            ))

    # Persist to Lakebase for historical tracking
    if quotes_to_persist and not db.is_demo_mode:
        saved = await save_market_quotes_batch(quotes_to_persist)
        print(f"[finnhub] Persisted {saved} stock quotes to Lakebase")

    result = {
        "quotes": [q.model_dump() for q in quotes],
        "updated_at": now
    }
    await cache_set(cache_key, result, MARKET_CACHE_TTL)
    return ListQuotesResponse(**result)


# CoinGecko API for crypto (free, no key required)
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
CRYPTO_CACHE_TTL = 120  # 2 minutes


@router.get("/list-crypto-quotes", response_model=ListQuotesResponse)
async def list_crypto_quotes(
    symbols: str = Query(",".join(CRYPTO), description="Comma-separated crypto symbols"),
):
    """Get real-time cryptocurrency quotes from CoinGecko.

    LAKEBASE-FIRST PATTERN:
    - Quotes are fetched from CoinGecko (free API) and persisted to Lakebase
    - Enables historical price tracking for time-based navigation
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    cache_key = f"crypto:{','.join(sorted(symbol_list))}"

    cached = await cache_get(cache_key)
    if cached:
        return ListQuotesResponse(**cached)

    quotes = []
    quotes_to_persist = []
    now = int(datetime.utcnow().timestamp() * 1000)

    # Map symbols to CoinGecko IDs
    symbol_to_id = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "LINK": "chainlink",
    }

    ids = [symbol_to_id.get(s, s.lower()) for s in symbol_list if s in symbol_to_id]

    if ids:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{COINGECKO_BASE_URL}/simple/price",
                    params={
                        "ids": ",".join(ids),
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true",
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    for symbol in symbol_list:
                        coin_id = symbol_to_id.get(symbol, symbol.lower())
                        if coin_id in data:
                            coin_data = data[coin_id]
                            price = float(coin_data.get("usd", 0))
                            change_pct = float(coin_data.get("usd_24h_change", 0) or 0)
                            volume = int(coin_data.get("usd_24h_vol", 0) or 0)
                            market_cap = float(coin_data.get("usd_market_cap", 0) or 0)

                            quote = Quote(
                                symbol=symbol,
                                name=coin_id.replace("-", " ").title(),
                                price=price,
                                change=price * change_pct / 100,
                                change_percent=change_pct,
                                volume=volume,
                                market_cap=market_cap,
                                timestamp=now,
                            )
                            quotes.append(quote)

                            # Prepare for Lakebase persistence
                            quotes_to_persist.append({
                                "symbol": symbol,
                                "asset_type": "crypto",
                                "name": coin_id.replace("-", " ").title(),
                                "price": price,
                                "change": price * change_pct / 100,
                                "change_percent": change_pct,
                                "volume": volume,
                                "market_cap": market_cap,
                            })
        except Exception as e:
            print(f"[coingecko] API error: {e}")

    # Persist to Lakebase for historical tracking
    if quotes_to_persist and not db.is_demo_mode:
        saved = await save_market_quotes_batch(quotes_to_persist)
        print(f"[coingecko] Persisted {saved} crypto quotes to Lakebase")

    result = {
        "quotes": [q.model_dump() for q in quotes],
        "updated_at": now
    }
    await cache_set(cache_key, result, CRYPTO_CACHE_TTL)
    return ListQuotesResponse(**result)


@router.get("/list-commodity-quotes", response_model=ListQuotesResponse)
async def list_commodity_quotes():
    """Get commodity quotes (Gold, Silver, Oil, Natural Gas)."""
    cache_key = "commodities:quotes"

    cached = await cache_get(cache_key)
    if cached:
        return ListQuotesResponse(**cached)

    # Use Finnhub for commodities if available
    quotes = []
    now = int(datetime.utcnow().timestamp() * 1000)

    commodity_names = {
        "GC=F": "Gold",
        "SI=F": "Silver",
        "CL=F": "Crude Oil",
        "NG=F": "Natural Gas",
    }

    # For demo, return placeholder data
    # In production, would use Finnhub or Yahoo Finance
    for symbol, name in commodity_names.items():
        quotes.append(Quote(
            symbol=symbol,
            name=name,
            price=0.0,
            change=0.0,
            change_percent=0.0,
            volume=None,
            market_cap=None,
            timestamp=now,
        ))

    result = {
        "quotes": [q.model_dump() for q in quotes],
        "updated_at": now
    }
    await cache_set(cache_key, result, MARKET_CACHE_TTL)
    return ListQuotesResponse(**result)


class QuoteHistoryResponse(BaseModel):
    symbol: str
    history: list[dict]
    total: int


@router.get("/quote-history/{symbol}", response_model=QuoteHistoryResponse)
async def get_symbol_quote_history(
    symbol: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to fetch"),
):
    """Get historical price data for a specific symbol from Lakebase.

    Enables time-based navigation for price charts.
    """
    symbol = symbol.upper()

    if db.is_demo_mode:
        return QuoteHistoryResponse(symbol=symbol, history=[], total=0)

    history = await get_quote_history(symbol, hours)

    return QuoteHistoryResponse(
        symbol=symbol,
        history=history,
        total=len(history),
    )


@router.get("/list-etf-flows", response_model=ListETFFlowsResponse)
async def list_etf_flows():
    """Get ETF fund flows data."""
    cache_key = "etf:flows"

    cached = await cache_get(cache_key)
    if cached:
        return ListETFFlowsResponse(**cached)

    # ETF flow data typically requires premium data sources
    # For now, return placeholder structure
    flows = [
        ETFFlow(
            symbol="SPY",
            name="SPDR S&P 500 ETF",
            flow_1d=0.0,
            flow_1w=0.0,
            flow_1m=0.0,
            aum=400e9,
            category="Large Cap Blend",
        ),
        ETFFlow(
            symbol="QQQ",
            name="Invesco QQQ Trust",
            flow_1d=0.0,
            flow_1w=0.0,
            flow_1m=0.0,
            aum=200e9,
            category="Large Cap Growth",
        ),
        ETFFlow(
            symbol="IWM",
            name="iShares Russell 2000 ETF",
            flow_1d=0.0,
            flow_1w=0.0,
            flow_1m=0.0,
            aum=60e9,
            category="Small Cap Blend",
        ),
    ]

    result = {
        "flows": [f.model_dump() for f in flows],
        "updated_at": int(datetime.utcnow().timestamp() * 1000)
    }
    await cache_set(cache_key, result, 3600)  # 1 hour cache
    return ListETFFlowsResponse(**result)
