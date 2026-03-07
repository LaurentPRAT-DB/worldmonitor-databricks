"""
Lakebase (PostgreSQL) database connection pool with OAuth token refresh.
Also supports reading from Unity Catalog for historical data.

HYBRID ARCHITECTURE:
- Lakebase: Real-time data (< LAKEBASE_RETENTION_HOURS) for fast UI interactions
- Unity Catalog: Historical data (> LAKEBASE_RETENTION_HOURS) for cost-effective storage
- API transparently merges both sources based on requested time range
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Any
from contextlib import asynccontextmanager
import asyncpg

from .config import get_oauth_token, get_lakebase_credential, get_workspace_host, settings, IS_DATABRICKS_APP

# Unity Catalog configuration for vessel history
UC_CATALOG = os.environ.get("UC_CATALOG", "serverless_stable_3n0ihb_catalog")
UC_SCHEMA = os.environ.get("UC_SCHEMA", "worldmonitor_dev")
UC_VESSEL_HISTORY_TABLE = "vessel_positions_history"

# Hybrid storage threshold: data older than this goes to Unity Catalog
# Lakebase handles recent data for fast UI, Unity Catalog for historical queries
LAKEBASE_RETENTION_HOURS = int(os.environ.get("LAKEBASE_RETENTION_HOURS", "24"))


class DatabasePool:
    """Async connection pool for Lakebase with automatic token refresh."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._demo_mode = False
        self._connection_failed = False
        self._token_refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def get_pool(self) -> Optional[asyncpg.Pool]:
        """Get or create the connection pool."""
        # Check for forced demo mode via config
        if settings.FORCE_DEMO_MODE:
            print("[db] FORCE_DEMO_MODE is set - running in demo mode")
            self._demo_mode = True
            return None

        if not settings.is_lakebase_configured():
            self._demo_mode = True
            return None

        async with self._lock:
            if self._pool is None:
                await self._create_pool()
            return self._pool

    async def _create_pool(self) -> None:
        """Create a new connection pool with Lakebase Autoscaling credential."""
        try:
            # For Lakebase Autoscaling, use postgres.generate_database_credential()
            token = get_lakebase_credential()
            if not token:
                error_msg = "[db] No Lakebase credential available"
                print(error_msg)
                if settings.FORCE_LAKEBASE:
                    raise RuntimeError(f"{error_msg} - FORCE_LAKEBASE is set, cannot continue")
                print("[db] Falling back to demo mode")
                self._demo_mode = True
                self._connection_failed = True
                self._pool = None
                return

            print(f"[db] Attempting connection to {settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE} as {settings.PGUSER}")
            self._pool = await asyncpg.create_pool(
                host=settings.PGHOST,
                port=settings.PGPORT,
                database=settings.PGDATABASE,
                user=settings.PGUSER,
                password=token,
                ssl="require",
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            self._demo_mode = False
            self._connection_failed = False
            print(f"[db] Connected to Lakebase Autoscaling: {settings.PGHOST}/{settings.PGDATABASE}")
        except Exception as e:
            error_msg = f"[db] Lakebase connection failed: {e}"
            print(error_msg)
            if settings.FORCE_LAKEBASE:
                raise RuntimeError(f"{error_msg} - FORCE_LAKEBASE is set, cannot continue")
            print("[db] Falling back to demo mode")
            self._demo_mode = True
            self._connection_failed = True
            self._pool = None

    async def refresh_token(self) -> None:
        """Refresh OAuth token by recreating the pool.

        Call this every ~45 minutes as Databricks OAuth tokens expire after 1 hour.
        """
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
            await self._create_pool()

    async def start_token_refresh_loop(self) -> None:
        """Start background task to refresh token every 45 minutes."""
        if self._token_refresh_task is None:
            self._token_refresh_task = asyncio.create_task(self._refresh_loop())

    async def _refresh_loop(self) -> None:
        """Background loop for token refresh."""
        while True:
            await asyncio.sleep(45 * 60)  # 45 minutes
            try:
                await self.refresh_token()
                print("[db] OAuth token refreshed successfully")
            except Exception as e:
                print(f"[db] Token refresh failed: {e}")

    async def close(self) -> None:
        """Close the connection pool."""
        if self._token_refresh_task:
            self._token_refresh_task.cancel()
            self._token_refresh_task = None
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode (no database).

        Controlled by environment variables:
        - FORCE_DEMO_MODE=true: Always run in demo mode
        - FORCE_LAKEBASE=true: Never run in demo mode (fail if DB unavailable)
        """
        # Config-level overrides
        if settings.FORCE_DEMO_MODE:
            return True
        if settings.FORCE_LAKEBASE:
            return False
        # Default: based on connection state
        return self._demo_mode

    def set_demo_mode(self, value: bool) -> None:
        """Manually set demo mode (for testing or admin override)."""
        self._demo_mode = value
        print(f"[db] Demo mode manually set to: {value}")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        pool = await self.get_pool()
        if pool is None:
            raise RuntimeError("Database not available (demo mode)")
        async with pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Execute a query and return all results."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a query and return the first row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """Execute a query and return a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        """Execute a query without returning results."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)


# Global database pool instance
db = DatabasePool()


# Cache table for API responses (replaces Upstash Redis)
CACHE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_cache_expires ON api_cache(expires_at);
"""

# Vessel position history table for route tracking
VESSEL_POSITIONS_DDL = """
CREATE TABLE IF NOT EXISTS vessel_positions (
    id BIGSERIAL PRIMARY KEY,
    mmsi TEXT NOT NULL,
    name TEXT,
    ship_type INTEGER DEFAULT 0,
    flag_country TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    speed DOUBLE PRECISION DEFAULT 0,
    course DOUBLE PRECISION DEFAULT 0,
    heading INTEGER DEFAULT 0,
    destination TEXT,
    is_synthetic BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vessel_positions_mmsi ON vessel_positions(mmsi);
CREATE INDEX IF NOT EXISTS idx_vessel_positions_recorded_at ON vessel_positions(recorded_at);
CREATE INDEX IF NOT EXISTS idx_vessel_positions_mmsi_time ON vessel_positions(mmsi, recorded_at DESC);
"""

# Earthquake table - 30 day retention in Lakebase
EARTHQUAKES_DDL = """
CREATE TABLE IF NOT EXISTS earthquakes (
    id TEXT PRIMARY KEY,
    magnitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    depth DOUBLE PRECISION DEFAULT 0,
    place TEXT,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    alert_level TEXT,
    tsunami_warning BOOLEAN DEFAULT FALSE,
    felt_reports INTEGER DEFAULT 0,
    url TEXT,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_earthquakes_occurred ON earthquakes(occurred_at);
CREATE INDEX IF NOT EXISTS idx_earthquakes_magnitude ON earthquakes(magnitude);
"""

# Conflict events table (UCDP) - 30 day retention in Lakebase
CONFLICT_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS conflict_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_type TEXT,
    country TEXT,
    admin1 TEXT,
    location_name TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fatalities INTEGER DEFAULT 0,
    actors TEXT[],
    notes TEXT,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_occurred ON conflict_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_conflicts_country ON conflict_events(country);
CREATE INDEX IF NOT EXISTS idx_conflicts_source ON conflict_events(source);
"""

# Fire detections table (NASA FIRMS) - 7 day retention in Lakebase
FIRE_DETECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS fire_detections (
    id BIGSERIAL PRIMARY KEY,
    fire_id TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    brightness DOUBLE PRECISION,
    confidence TEXT,
    satellite TEXT,
    frp DOUBLE PRECISION,
    daynight TEXT,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(latitude, longitude, detected_at)
);

CREATE INDEX IF NOT EXISTS idx_fires_detected ON fire_detections(detected_at);
CREATE INDEX IF NOT EXISTS idx_fires_location ON fire_detections(latitude, longitude);
"""

# Market quotes history table - 24 hour retention in Lakebase
MARKET_QUOTES_DDL = """
CREATE TABLE IF NOT EXISTS market_quotes_history (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    name TEXT,
    price DOUBLE PRECISION NOT NULL,
    change DOUBLE PRECISION DEFAULT 0,
    change_percent DOUBLE PRECISION DEFAULT 0,
    volume BIGINT,
    market_cap DOUBLE PRECISION,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quotes_symbol_time ON market_quotes_history(symbol, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_asset_type ON market_quotes_history(asset_type);
"""

# Retention hours by data type
RETENTION_HOURS = {
    "earthquakes": 720,      # 30 days
    "conflicts": 720,        # 30 days
    "fires": 168,            # 7 days
    "market_quotes": 24,     # 24 hours
    "vessels": LAKEBASE_RETENTION_HOURS,  # Default 24 hours
}


async def init_cache_table() -> None:
    """Initialize the cache table if Lakebase is available."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            await conn.execute(CACHE_TABLE_DDL)
        print("[db] Cache table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize cache table: {e}")


async def init_vessel_positions_table() -> None:
    """Initialize the vessel positions table for route tracking."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            await conn.execute(VESSEL_POSITIONS_DDL)
        print("[db] Vessel positions table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize vessel positions table: {e}")


async def init_earthquakes_table() -> None:
    """Initialize the earthquakes table for seismic data persistence."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            # Check if table exists with correct schema by checking for a specific column
            check_sql = """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'earthquakes' AND column_name = 'tsunami_warning'
            """
            result = await conn.fetchrow(check_sql)

            if result is None:
                # Table is missing columns or doesn't exist at all - drop and recreate
                print("[db] Earthquakes table schema mismatch - recreating table")
                await conn.execute("DROP TABLE IF EXISTS earthquakes CASCADE")

            # Create table (will do nothing if already correct schema)
            await conn.execute(EARTHQUAKES_DDL)
        print("[db] Earthquakes table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize earthquakes table: {e}")


async def init_conflict_events_table() -> None:
    """Initialize the conflict events table for UCDP data persistence."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            await conn.execute(CONFLICT_EVENTS_DDL)
        print("[db] Conflict events table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize conflict events table: {e}")


async def init_fire_detections_table() -> None:
    """Initialize the fire detections table for NASA FIRMS data persistence."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            await conn.execute(FIRE_DETECTIONS_DDL)
        print("[db] Fire detections table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize fire detections table: {e}")


async def init_market_quotes_table() -> None:
    """Initialize the market quotes history table for price tracking."""
    if not settings.is_lakebase_configured():
        return
    try:
        async with db.acquire() as conn:
            await conn.execute(MARKET_QUOTES_DDL)
        print("[db] Market quotes history table initialized")
    except Exception as e:
        print(f"[db] Failed to initialize market quotes table: {e}")


async def init_all_tables() -> None:
    """Initialize all Lakebase tables."""
    await init_cache_table()
    await init_vessel_positions_table()
    await init_earthquakes_table()
    await init_conflict_events_table()
    await init_fire_detections_table()
    await init_market_quotes_table()


async def cache_get(key: str) -> Optional[dict]:
    """Get a value from the cache."""
    import json
    if db.is_demo_mode:
        return None
    try:
        row = await db.fetchrow(
            "SELECT value FROM api_cache WHERE cache_key = $1 AND expires_at > NOW()",
            key
        )
        if row:
            val = row["value"]
            # Handle both JSONB (returns dict) and TEXT (returns string)
            if isinstance(val, dict):
                return val
            return json.loads(val)
        return None
    except Exception:
        return None


async def cache_set(key: str, value: dict, ttl_seconds: int = 300) -> None:
    """Set a value in the cache with TTL.

    Uses explicit JSON serialization for compatibility with both TEXT and JSONB columns.
    """
    import json
    if db.is_demo_mode:
        return
    try:
        # Serialize dict to JSON string for storage
        value_json = json.dumps(value)
        await db.execute(
            """
            INSERT INTO api_cache (cache_key, value, expires_at)
            VALUES ($1, $2::jsonb, NOW() + INTERVAL '1 second' * $3)
            ON CONFLICT (cache_key) DO UPDATE SET
                value = EXCLUDED.value,
                expires_at = EXCLUDED.expires_at
            """,
            key, value_json, ttl_seconds
        )
    except Exception as e:
        print(f"[cache] Failed to set {key}: {e}")


async def cache_delete(key: str) -> None:
    """Delete a value from the cache."""
    if db.is_demo_mode:
        return
    try:
        await db.execute("DELETE FROM api_cache WHERE cache_key = $1", key)
    except Exception:
        pass


async def cleanup_expired_cache() -> int:
    """Remove expired cache entries. Returns count of deleted rows."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute("DELETE FROM api_cache WHERE expires_at < NOW()")
        # Parse "DELETE N" response
        return int(result.split()[-1]) if result else 0
    except Exception:
        return 0


# Vessel position tracking functions

async def save_vessel_position(
    mmsi: str,
    latitude: float,
    longitude: float,
    name: str = None,
    ship_type: int = 0,
    flag_country: str = None,
    speed: float = 0,
    course: float = 0,
    heading: int = 0,
    destination: str = None,
    is_synthetic: bool = False,
) -> bool:
    """Save a vessel position to the history table."""
    if db.is_demo_mode:
        return False
    try:
        await db.execute(
            """
            INSERT INTO vessel_positions
            (mmsi, name, ship_type, flag_country, latitude, longitude, speed, course, heading, destination, is_synthetic)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            mmsi, name, ship_type, flag_country, latitude, longitude, speed, course, heading, destination, is_synthetic
        )
        return True
    except Exception as e:
        print(f"[db] Failed to save vessel position: {e}")
        return False


async def save_vessel_positions_batch(vessels: list[dict]) -> int:
    """Save multiple vessel positions in a batch. Returns count of saved positions."""
    if db.is_demo_mode or not vessels:
        return 0
    try:
        async with db.acquire() as conn:
            # Use executemany for batch insert
            await conn.executemany(
                """
                INSERT INTO vessel_positions
                (mmsi, name, ship_type, flag_country, latitude, longitude, speed, course, heading, destination, is_synthetic)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                [
                    (
                        v.get("mmsi"),
                        v.get("name"),
                        v.get("ship_type", 0),
                        v.get("flag_country"),
                        v.get("latitude"),
                        v.get("longitude"),
                        v.get("speed", 0),
                        v.get("course", 0),
                        v.get("heading", 0),
                        v.get("destination"),
                        v.get("is_synthetic", False),
                    )
                    for v in vessels
                ]
            )
        return len(vessels)
    except Exception as e:
        print(f"[db] Failed to save vessel positions batch: {e}")
        return 0


async def get_vessel_route(mmsi: str, hours_back: int = 24) -> list[dict]:
    """Get position history for a specific vessel within the time range."""
    if db.is_demo_mode:
        return []
    try:
        rows = await db.fetch(
            """
            SELECT mmsi, name, latitude, longitude, speed, course, heading, destination,
                   is_synthetic, recorded_at
            FROM vessel_positions
            WHERE mmsi = $1 AND recorded_at > NOW() - INTERVAL '1 hour' * $2
            ORDER BY recorded_at ASC
            """,
            mmsi, hours_back
        )
        return [
            {
                "mmsi": r["mmsi"],
                "name": r["name"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "speed": r["speed"],
                "course": r["course"],
                "heading": r["heading"],
                "destination": r["destination"],
                "is_synthetic": r["is_synthetic"],
                "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get vessel route: {e}")
        return []


async def get_all_vessel_routes(hours_back: int = 24, max_points_per_vessel: int = 20) -> dict[str, list[dict]]:
    """Get position history for all vessels within the time range, grouped by MMSI.

    HYBRID ARCHITECTURE:
    - If hours_back <= LAKEBASE_RETENTION_HOURS: Query Lakebase only (fast)
    - If hours_back > LAKEBASE_RETENTION_HOURS: Query both sources and merge
      - Lakebase: recent data (last LAKEBASE_RETENTION_HOURS)
      - Unity Catalog: historical data (older than LAKEBASE_RETENTION_HOURS)

    max_points_per_vessel: Limit points per vessel to avoid long straight lines from sparse data.
                           Uses the most recent points for each vessel.

    This provides fast UI response for recent data while supporting long historical queries.
    """
    routes: dict[str, list[dict]] = {}

    # Determine query strategy based on time range
    use_lakebase = not db.is_demo_mode
    use_unity_catalog = hours_back > LAKEBASE_RETENTION_HOURS or db.is_demo_mode

    lakebase_hours = min(hours_back, LAKEBASE_RETENTION_HOURS) if use_lakebase else 0
    unity_catalog_hours = hours_back if use_unity_catalog else 0

    print(f"[db] Hybrid query: hours_back={hours_back}, lakebase={lakebase_hours}h, uc={unity_catalog_hours}h")

    # Query Lakebase for recent data
    if use_lakebase and lakebase_hours > 0:
        try:
            rows = await db.fetch(
                """
                SELECT mmsi, name, latitude, longitude, speed, course, heading, destination,
                       is_synthetic, recorded_at
                FROM vessel_positions
                WHERE recorded_at > NOW() - INTERVAL '1 hour' * $1
                ORDER BY mmsi, recorded_at ASC
                """,
                lakebase_hours
            )
            # Group by MMSI
            for r in rows:
                mmsi = r["mmsi"]
                if mmsi not in routes:
                    routes[mmsi] = []
                routes[mmsi].append({
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "speed": r["speed"],
                    "course": r["course"],
                    "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
                })

            if routes:
                print(f"[db] Got {len(routes)} vessel routes from Lakebase (recent {lakebase_hours}h)")

                # If we only need Lakebase data, return now
                if hours_back <= LAKEBASE_RETENTION_HOURS:
                    # Only limit points for routes with large gaps
                    routes = _limit_routes_with_gaps(routes, max_points_per_vessel)
                    return routes
        except Exception as e:
            print(f"[db] Failed to get vessel routes from Lakebase: {e}")

    # Query Unity Catalog for historical data (or as fallback)
    if use_unity_catalog:
        print(f"[db] Querying Unity Catalog for historical data ({unity_catalog_hours}h)")
        uc_routes = await get_vessel_routes_from_unity_catalog(unity_catalog_hours)

        if uc_routes:
            print(f"[db] Got {len(uc_routes)} vessel routes from Unity Catalog")

            # Merge Unity Catalog data with Lakebase data
            routes = _merge_vessel_routes(uc_routes, routes)
            print(f"[db] Merged routes: {len(routes)} vessels total")

    # Only limit points if there are large gaps in the data
    # This preserves full routes when data is continuous, but trims when sparse
    routes = _limit_routes_with_gaps(routes, max_points_per_vessel)

    return routes


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers."""
    import math
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def _has_large_gaps(points: list[dict], gap_threshold_km: float = 500) -> bool:
    """Check if route has any gaps larger than threshold between consecutive points."""
    if len(points) < 2:
        return False

    for i in range(1, len(points)):
        prev = points[i-1]
        curr = points[i]
        distance = _haversine_distance(
            prev["latitude"], prev["longitude"],
            curr["latitude"], curr["longitude"]
        )
        if distance > gap_threshold_km:
            return True
    return False


def _limit_routes_with_gaps(
    routes: dict[str, list[dict]],
    max_points: int = 20,
    gap_threshold_km: float = 500
) -> dict[str, list[dict]]:
    """Limit route points only for vessels with large gaps in their data.

    If a route has consecutive points more than gap_threshold_km apart,
    trim to the last max_points to avoid weird straight lines across the globe.
    Otherwise, keep all points for continuous routes.
    """
    result = {}
    for mmsi, points in routes.items():
        if _has_large_gaps(points, gap_threshold_km):
            # Has gaps - use only last N points
            result[mmsi] = points[-max_points:] if len(points) > max_points else points
        else:
            # No gaps - keep all points
            result[mmsi] = points
    return result


def _merge_vessel_routes(
    historical: dict[str, list[dict]],
    recent: dict[str, list[dict]]
) -> dict[str, list[dict]]:
    """Merge historical (Unity Catalog) and recent (Lakebase) route data.

    Historical data comes first, recent data appended, sorted by timestamp.
    Deduplicates based on recorded_at timestamp.
    """
    merged: dict[str, list[dict]] = {}

    # Get all MMSIs from both sources
    all_mmsis = set(historical.keys()) | set(recent.keys())

    for mmsi in all_mmsis:
        hist_points = historical.get(mmsi, [])
        recent_points = recent.get(mmsi, [])

        # Combine and deduplicate by timestamp
        seen_timestamps = set()
        combined = []

        for point in hist_points + recent_points:
            ts = point.get("recorded_at")
            if ts and ts not in seen_timestamps:
                seen_timestamps.add(ts)
                combined.append(point)

        # Sort by timestamp
        combined.sort(key=lambda p: p.get("recorded_at") or "")

        if combined:
            merged[mmsi] = combined

    return merged


async def cleanup_old_vessel_positions(days_to_keep: int = 30) -> int:
    """Remove vessel positions older than specified days. Returns count of deleted rows."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute(
            "DELETE FROM vessel_positions WHERE recorded_at < NOW() - INTERVAL '1 day' * $1",
            days_to_keep
        )
        return int(result.split()[-1]) if result else 0
    except Exception as e:
        print(f"[db] Failed to cleanup old vessel positions: {e}")
        return 0


# Unity Catalog query functions for vessel history

async def query_unity_catalog(sql: str) -> list[dict]:
    """Execute SQL query against Unity Catalog using Statement Execution API."""
    host = get_workspace_host()
    token = get_oauth_token()
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")

    if not host or not token:
        print("[db] Unity Catalog query failed: missing host or token")
        return []

    if not warehouse_id:
        print("[db] Unity Catalog query failed: DATABRICKS_WAREHOUSE_ID not set")
        return []

    url = f"{host}/api/2.0/sql/statements"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": "30s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"[db] Unity Catalog query failed: {resp.status} - {error_text}")
                    return []

                data = await resp.json()

                # Check status
                status = data.get("status", {}).get("state", "")
                if status == "FAILED":
                    error = data.get("status", {}).get("error", {})
                    print(f"[db] Unity Catalog query failed: {error}")
                    return []

                # Parse results
                manifest = data.get("manifest", {})
                columns = [col["name"] for col in manifest.get("schema", {}).get("columns", [])]
                result_data = data.get("result", {}).get("data_array", [])

                # Convert to list of dicts
                return [dict(zip(columns, row)) for row in result_data]

    except Exception as e:
        print(f"[db] Unity Catalog query error: {e}")
        return []


async def get_vessel_routes_from_unity_catalog(hours_back: int = 24) -> dict[str, list[dict]]:
    """Get vessel routes from Unity Catalog table.

    This is used when Lakebase doesn't have the historical data.
    The data was generated by the generate_vessel_history notebook.
    """
    table = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_VESSEL_HISTORY_TABLE}"

    sql = f"""
    SELECT mmsi, name, latitude, longitude, speed, course, recorded_at
    FROM {table}
    WHERE recorded_at > current_timestamp() - INTERVAL {hours_back} HOURS
    ORDER BY mmsi, recorded_at ASC
    """

    rows = await query_unity_catalog(sql)

    if not rows:
        return {}

    # Group by MMSI
    routes: dict[str, list[dict]] = {}
    for r in rows:
        mmsi = r.get("mmsi", "")
        if mmsi not in routes:
            routes[mmsi] = []

        recorded_at = r.get("recorded_at")
        if isinstance(recorded_at, str):
            recorded_at_str = recorded_at
        else:
            recorded_at_str = str(recorded_at) if recorded_at else None

        routes[mmsi].append({
            "latitude": float(r.get("latitude", 0)),
            "longitude": float(r.get("longitude", 0)),
            "speed": float(r.get("speed", 0)),
            "course": float(r.get("course", 0)),
            "recorded_at": recorded_at_str,
        })

    return routes


# =============================================================================
# EARTHQUAKE PERSISTENCE FUNCTIONS
# =============================================================================

async def save_earthquake(earthquake: dict) -> bool:
    """Save a single earthquake to Lakebase."""
    if db.is_demo_mode:
        return False
    try:
        await db.execute(
            """
            INSERT INTO earthquakes
            (id, magnitude, latitude, longitude, depth, place, occurred_at, alert_level, tsunami_warning, felt_reports, url)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (id) DO UPDATE SET
                magnitude = EXCLUDED.magnitude,
                fetched_at = NOW()
            """,
            earthquake.get("id"),
            earthquake.get("magnitude", 0),
            earthquake.get("latitude", 0),
            earthquake.get("longitude", 0),
            earthquake.get("depth", 0),
            earthquake.get("place"),
            datetime.fromtimestamp(earthquake.get("occurred_at", 0) / 1000, tz=timezone.utc),
            earthquake.get("alert_level"),
            earthquake.get("tsunami_warning", False),
            earthquake.get("felt_reports", 0),
            earthquake.get("url"),
        )
        return True
    except Exception as e:
        print(f"[db] Failed to save earthquake: {e}")
        return False


async def save_earthquakes_batch(earthquakes: list[dict]) -> int:
    """Save multiple earthquakes to Lakebase. Returns count saved."""
    if db.is_demo_mode or not earthquakes:
        return 0

    saved = 0
    for eq in earthquakes:
        if await save_earthquake(eq):
            saved += 1
    return saved


async def get_earthquakes_from_lakebase(
    hours_back: int = 168,
    min_magnitude: float = 0,
) -> list[dict]:
    """Get earthquakes from Lakebase within time range."""
    if db.is_demo_mode:
        return []
    try:
        rows = await db.fetch(
            """
            SELECT id, magnitude, latitude, longitude, depth, place,
                   occurred_at, alert_level, tsunami_warning, felt_reports, url
            FROM earthquakes
            WHERE occurred_at > NOW() - INTERVAL '1 hour' * $1
              AND magnitude >= $2
            ORDER BY occurred_at DESC
            """,
            hours_back, min_magnitude
        )
        return [
            {
                "id": r["id"],
                "magnitude": r["magnitude"],
                "location": {
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "depth": r["depth"],
                },
                "place": r["place"],
                "occurred_at": int(r["occurred_at"].timestamp() * 1000) if r["occurred_at"] else 0,
                "alert_level": r["alert_level"],
                "tsunami_warning": r["tsunami_warning"],
                "felt_reports": r["felt_reports"],
                "url": r["url"],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get earthquakes: {e}")
        return []


async def cleanup_old_earthquakes(hours_to_keep: int = 720) -> int:
    """Remove earthquakes older than specified hours."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute(
            "DELETE FROM earthquakes WHERE occurred_at < NOW() - INTERVAL '1 hour' * $1",
            hours_to_keep
        )
        return int(result.split()[-1]) if result else 0
    except Exception:
        return 0


# =============================================================================
# CONFLICT EVENT PERSISTENCE FUNCTIONS
# =============================================================================

async def save_conflict_event(event: dict) -> bool:
    """Save a single conflict event to Lakebase."""
    if db.is_demo_mode:
        return False
    try:
        # Ensure location_name is string or None
        location_name = event.get("location_name")
        if location_name is not None and not isinstance(location_name, str):
            location_name = str(location_name)

        await db.execute(
            """
            INSERT INTO conflict_events
            (id, source, event_type, country, admin1, location_name, latitude, longitude, occurred_at, fatalities, actors, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO UPDATE SET
                fatalities = EXCLUDED.fatalities,
                fetched_at = NOW()
            """,
            event.get("id"),
            event.get("source", "ucdp"),
            event.get("event_type"),
            event.get("country"),
            event.get("admin1"),
            location_name,
            event.get("latitude", 0),
            event.get("longitude", 0),
            datetime.fromtimestamp(event.get("occurred_at", 0) / 1000, tz=timezone.utc),
            event.get("fatalities", 0),
            event.get("actors", []),
            event.get("notes"),
        )
        return True
    except Exception as e:
        print(f"[db] Failed to save conflict event {event.get('id')}: {e}")
        return False


async def save_conflict_events_batch(events: list[dict]) -> int:
    """Save multiple conflict events to Lakebase. Returns count saved."""
    if db.is_demo_mode or not events:
        return 0

    saved = 0
    for event in events:
        if await save_conflict_event(event):
            saved += 1
    return saved


async def get_conflicts_from_lakebase(
    hours_back: int = 168,
    source: str = None,
    country: str = None,
) -> list[dict]:
    """Get conflict events from Lakebase within time range."""
    if db.is_demo_mode:
        return []
    try:
        query = """
            SELECT id, source, event_type, country, admin1, location_name,
                   latitude, longitude, occurred_at, fatalities, actors, notes
            FROM conflict_events
            WHERE occurred_at > NOW() - INTERVAL '1 hour' * $1
        """
        params = [hours_back]

        if source:
            query += " AND source = $2"
            params.append(source)

        if country:
            idx = len(params) + 1
            query += f" AND country = ${idx}"
            params.append(country)

        query += " ORDER BY occurred_at DESC"

        rows = await db.fetch(query, *params)
        return [
            {
                "id": r["id"],
                "source": r["source"],
                "event_type": r["event_type"],
                "country": r["country"],
                "admin1": r["admin1"],
                "location": {"latitude": r["latitude"], "longitude": r["longitude"]},
                "occurred_at": int(r["occurred_at"].timestamp() * 1000) if r["occurred_at"] else 0,
                "fatalities": r["fatalities"],
                "actors": r["actors"] or [],
                "notes": r["notes"],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get conflicts: {e}")
        return []


async def cleanup_old_conflicts(hours_to_keep: int = 720) -> int:
    """Remove conflict events older than specified hours."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute(
            "DELETE FROM conflict_events WHERE occurred_at < NOW() - INTERVAL '1 hour' * $1",
            hours_to_keep
        )
        return int(result.split()[-1]) if result else 0
    except Exception:
        return 0


# =============================================================================
# FIRE DETECTION PERSISTENCE FUNCTIONS
# =============================================================================

async def save_fire_detection(fire: dict) -> bool:
    """Save a single fire detection to Lakebase."""
    if db.is_demo_mode:
        return False
    try:
        await db.execute(
            """
            INSERT INTO fire_detections
            (fire_id, latitude, longitude, brightness, confidence, satellite, frp, daynight, detected_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (latitude, longitude, detected_at) DO NOTHING
            """,
            fire.get("fire_id"),
            fire.get("latitude", 0),
            fire.get("longitude", 0),
            fire.get("brightness", 0),
            fire.get("confidence"),
            fire.get("satellite"),
            fire.get("frp", 0),
            fire.get("daynight"),
            datetime.fromtimestamp(fire.get("detected_at", 0) / 1000, tz=timezone.utc),
        )
        return True
    except Exception as e:
        print(f"[db] Failed to save fire detection: {e}")
        return False


async def save_fire_detections_batch(fires: list[dict]) -> int:
    """Save multiple fire detections to Lakebase. Returns count saved."""
    if db.is_demo_mode or not fires:
        return 0

    saved = 0
    for fire in fires:
        if await save_fire_detection(fire):
            saved += 1
    return saved


async def get_fires_from_lakebase(hours_back: int = 24) -> list[dict]:
    """Get fire detections from Lakebase within time range."""
    if db.is_demo_mode:
        return []
    try:
        rows = await db.fetch(
            """
            SELECT id, fire_id, latitude, longitude, brightness, confidence,
                   satellite, frp, daynight, detected_at
            FROM fire_detections
            WHERE detected_at > NOW() - INTERVAL '1 hour' * $1
            ORDER BY detected_at DESC
            """,
            hours_back
        )
        return [
            {
                "id": str(r["id"]),
                "fire_id": r["fire_id"],
                "location": {"latitude": r["latitude"], "longitude": r["longitude"]},
                "brightness": r["brightness"],
                "confidence": r["confidence"],
                "satellite": r["satellite"],
                "frp": r["frp"],
                "daynight": r["daynight"],
                "detected_at": int(r["detected_at"].timestamp() * 1000) if r["detected_at"] else 0,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get fires: {e}")
        return []


async def cleanup_old_fires(hours_to_keep: int = 168) -> int:
    """Remove fire detections older than specified hours (default 7 days)."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute(
            "DELETE FROM fire_detections WHERE detected_at < NOW() - INTERVAL '1 hour' * $1",
            hours_to_keep
        )
        return int(result.split()[-1]) if result else 0
    except Exception:
        return 0


# =============================================================================
# MARKET QUOTES PERSISTENCE FUNCTIONS
# =============================================================================

async def save_market_quote(quote: dict) -> bool:
    """Save a single market quote to history table."""
    if db.is_demo_mode:
        return False
    try:
        await db.execute(
            """
            INSERT INTO market_quotes_history
            (symbol, asset_type, name, price, change, change_percent, volume, market_cap)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            quote.get("symbol"),
            quote.get("asset_type", "stock"),
            quote.get("name"),
            quote.get("price", 0),
            quote.get("change", 0),
            quote.get("change_percent", 0),
            quote.get("volume"),
            quote.get("market_cap"),
        )
        return True
    except Exception as e:
        print(f"[db] Failed to save market quote: {e}")
        return False


async def save_market_quotes_batch(quotes: list[dict]) -> int:
    """Save multiple market quotes to history. Returns count saved."""
    if db.is_demo_mode or not quotes:
        return 0

    saved = 0
    for quote in quotes:
        if await save_market_quote(quote):
            saved += 1
    return saved


async def get_market_quotes_from_lakebase(
    hours_back: int = 24,
    asset_type: str = None,
    symbols: list[str] = None,
) -> list[dict]:
    """Get most recent quote for each symbol from Lakebase."""
    if db.is_demo_mode:
        return []
    try:
        query = """
            SELECT DISTINCT ON (symbol)
                   symbol, asset_type, name, price, change, change_percent,
                   volume, market_cap, recorded_at
            FROM market_quotes_history
            WHERE recorded_at > NOW() - INTERVAL '1 hour' * $1
        """
        params = [hours_back]

        if asset_type:
            query = query.replace("WHERE", f"WHERE asset_type = ${len(params) + 1} AND")
            params.append(asset_type)

        if symbols:
            idx = len(params) + 1
            query = query.replace(
                "WHERE recorded_at",
                f"WHERE symbol = ANY(${idx}) AND recorded_at"
            )
            params.append(symbols)

        query += " ORDER BY symbol, recorded_at DESC"

        rows = await db.fetch(query, *params)
        return [
            {
                "symbol": r["symbol"],
                "asset_type": r["asset_type"],
                "name": r["name"],
                "price": r["price"],
                "change": r["change"],
                "change_percent": r["change_percent"],
                "volume": r["volume"],
                "market_cap": r["market_cap"],
                "timestamp": int(r["recorded_at"].timestamp() * 1000) if r["recorded_at"] else 0,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get market quotes: {e}")
        return []


async def get_quote_history(
    symbol: str,
    hours_back: int = 24,
) -> list[dict]:
    """Get price history for a specific symbol."""
    if db.is_demo_mode:
        return []
    try:
        rows = await db.fetch(
            """
            SELECT symbol, price, change_percent, recorded_at
            FROM market_quotes_history
            WHERE symbol = $1
              AND recorded_at > NOW() - INTERVAL '1 hour' * $2
            ORDER BY recorded_at ASC
            """,
            symbol, hours_back
        )
        return [
            {
                "symbol": r["symbol"],
                "price": r["price"],
                "change_percent": r["change_percent"],
                "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get quote history: {e}")
        return []


async def cleanup_old_quotes(hours_to_keep: int = 24) -> int:
    """Remove market quotes older than specified hours."""
    if db.is_demo_mode:
        return 0
    try:
        result = await db.execute(
            "DELETE FROM market_quotes_history WHERE recorded_at < NOW() - INTERVAL '1 hour' * $1",
            hours_to_keep
        )
        return int(result.split()[-1]) if result else 0
    except Exception:
        return 0


# =============================================================================
# ARCHIVAL FUNCTIONS - Move old Lakebase data to Unity Catalog
# =============================================================================

async def get_lakebase_positions_for_archival(hours_old: int = 24) -> list[dict]:
    """Get vessel positions from Lakebase that are older than threshold for archival.

    Returns positions older than `hours_old` hours for migration to Unity Catalog.
    """
    if db.is_demo_mode:
        return []

    try:
        rows = await db.fetch(
            """
            SELECT mmsi, name, ship_type, flag_country, latitude, longitude,
                   speed, course, heading, destination, is_synthetic, recorded_at
            FROM vessel_positions
            WHERE recorded_at < NOW() - INTERVAL '1 hour' * $1
            ORDER BY recorded_at ASC
            LIMIT 10000
            """,
            hours_old
        )
        return [
            {
                "mmsi": r["mmsi"],
                "name": r["name"],
                "ship_type": r["ship_type"],
                "flag_country": r["flag_country"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "speed": r["speed"],
                "course": r["course"],
                "heading": r["heading"],
                "destination": r["destination"],
                "is_synthetic": r["is_synthetic"],
                "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[db] Failed to get positions for archival: {e}")
        return []


async def delete_archived_positions(cutoff_hours: int = 24) -> int:
    """Delete positions from Lakebase that have been archived to Unity Catalog.

    Call this AFTER successfully archiving to Unity Catalog.
    Returns count of deleted rows.
    """
    if db.is_demo_mode:
        return 0

    try:
        result = await db.execute(
            """
            DELETE FROM vessel_positions
            WHERE recorded_at < NOW() - INTERVAL '1 hour' * $1
            """,
            cutoff_hours
        )
        deleted = int(result.split()[-1]) if result else 0
        print(f"[db] Deleted {deleted} archived positions from Lakebase")
        return deleted
    except Exception as e:
        print(f"[db] Failed to delete archived positions: {e}")
        return 0


async def archive_to_unity_catalog(positions: list[dict]) -> bool:
    """Archive vessel positions to Unity Catalog Delta table.

    Uses SQL INSERT to append positions to the history table.
    Returns True if successful.
    """
    if not positions:
        return True

    table = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_VESSEL_HISTORY_TABLE}"

    # Build INSERT statement with VALUES
    values_list = []
    for p in positions:
        # Escape strings and handle nulls
        mmsi = f"'{p['mmsi']}'" if p.get('mmsi') else 'NULL'
        name = f"'{p['name'].replace(chr(39), chr(39)+chr(39))}'" if p.get('name') else 'NULL'
        ship_type = p.get('ship_type', 0) or 0
        flag = f"'{p['flag_country']}'" if p.get('flag_country') else 'NULL'
        lat = p.get('latitude', 0)
        lon = p.get('longitude', 0)
        speed = p.get('speed', 0)
        course = p.get('course', 0)
        heading = p.get('heading', 0)
        dest = f"'{p['destination'].replace(chr(39), chr(39)+chr(39))}'" if p.get('destination') else 'NULL'
        synthetic = 'TRUE' if p.get('is_synthetic') else 'FALSE'
        recorded = f"TIMESTAMP '{p['recorded_at']}'" if p.get('recorded_at') else 'current_timestamp()'

        values_list.append(
            f"({mmsi}, {name}, {ship_type}, {flag}, {lat}, {lon}, {speed}, {course}, {heading}, {dest}, {synthetic}, {recorded})"
        )

    # Batch inserts (max 100 per statement to avoid query size limits)
    batch_size = 100
    for i in range(0, len(values_list), batch_size):
        batch = values_list[i:i + batch_size]
        sql = f"""
        INSERT INTO {table}
        (mmsi, name, ship_type, flag_country, latitude, longitude, speed, course, heading, destination, is_synthetic, recorded_at)
        VALUES {', '.join(batch)}
        """

        result = await query_unity_catalog(sql)
        # INSERT returns empty result on success
        if result is None:
            print(f"[db] Failed to archive batch {i//batch_size + 1}")
            return False

    print(f"[db] Archived {len(positions)} positions to Unity Catalog")
    return True


async def run_archival_cycle() -> dict:
    """Run a complete archival cycle: Lakebase -> Unity Catalog.

    1. Get positions older than LAKEBASE_RETENTION_HOURS from Lakebase
    2. Archive them to Unity Catalog
    3. Delete archived positions from Lakebase

    Returns summary dict with counts.
    """
    summary = {
        "positions_found": 0,
        "positions_archived": 0,
        "positions_deleted": 0,
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Get old positions from Lakebase
        positions = await get_lakebase_positions_for_archival(LAKEBASE_RETENTION_HOURS)
        summary["positions_found"] = len(positions)

        if not positions:
            summary["success"] = True
            print("[db] No positions to archive")
            return summary

        # Step 2: Archive to Unity Catalog
        archived = await archive_to_unity_catalog(positions)
        if not archived:
            summary["error"] = "Failed to archive to Unity Catalog"
            return summary

        summary["positions_archived"] = len(positions)

        # Step 3: Delete from Lakebase
        deleted = await delete_archived_positions(LAKEBASE_RETENTION_HOURS)
        summary["positions_deleted"] = deleted
        summary["success"] = True

        print(f"[db] Archival complete: {len(positions)} archived, {deleted} deleted")
        return summary

    except Exception as e:
        summary["error"] = str(e)
        print(f"[db] Archival cycle failed: {e}")
        return summary
