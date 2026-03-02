"""
Lakebase (PostgreSQL) database connection pool with OAuth token refresh.
"""

import os
import asyncio
from typing import Optional, Any
from contextlib import asynccontextmanager
import asyncpg

from .config import get_oauth_token, settings, IS_DATABRICKS_APP


class DatabasePool:
    """Async connection pool for Lakebase with automatic token refresh."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._demo_mode = False
        self._token_refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def get_pool(self) -> Optional[asyncpg.Pool]:
        """Get or create the connection pool."""
        if not settings.is_lakebase_configured():
            self._demo_mode = True
            return None

        async with self._lock:
            if self._pool is None:
                await self._create_pool()
            return self._pool

    async def _create_pool(self) -> None:
        """Create a new connection pool with current OAuth token."""
        try:
            token = get_oauth_token()
            if not token:
                print("[db] No OAuth token available - falling back to demo mode")
                self._demo_mode = True
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
            print(f"[db] Connected to Lakebase: {settings.PGHOST}/{settings.PGDATABASE}")
        except Exception as e:
            print(f"[db] Lakebase connection failed: {e}")
            self._demo_mode = True
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
        """Check if running in demo mode (no database)."""
        return self._demo_mode

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


async def cache_get(key: str) -> Optional[dict]:
    """Get a value from the cache."""
    if db.is_demo_mode:
        return None
    try:
        row = await db.fetchrow(
            "SELECT value FROM api_cache WHERE cache_key = $1 AND expires_at > NOW()",
            key
        )
        return dict(row["value"]) if row else None
    except Exception:
        return None


async def cache_set(key: str, value: dict, ttl_seconds: int = 300) -> None:
    """Set a value in the cache with TTL."""
    if db.is_demo_mode:
        return
    try:
        await db.execute(
            """
            INSERT INTO api_cache (cache_key, value, expires_at)
            VALUES ($1, $2, NOW() + INTERVAL '1 second' * $3)
            ON CONFLICT (cache_key) DO UPDATE SET
                value = EXCLUDED.value,
                expires_at = EXCLUDED.expires_at
            """,
            key, value, ttl_seconds
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


async def get_all_vessel_routes(hours_back: int = 24) -> dict[str, list[dict]]:
    """Get position history for all vessels within the time range, grouped by MMSI."""
    if db.is_demo_mode:
        return {}
    try:
        rows = await db.fetch(
            """
            SELECT mmsi, name, latitude, longitude, speed, course, heading, destination,
                   is_synthetic, recorded_at
            FROM vessel_positions
            WHERE recorded_at > NOW() - INTERVAL '1 hour' * $1
            ORDER BY mmsi, recorded_at ASC
            """,
            hours_back
        )
        # Group by MMSI
        routes: dict[str, list[dict]] = {}
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
        return routes
    except Exception as e:
        print(f"[db] Failed to get all vessel routes: {e}")
        return {}


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
