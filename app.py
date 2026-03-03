"""
World Monitor - Databricks App Entry Point

A real-time global intelligence dashboard ported to Databricks Apps
with FastAPI backend and React frontend.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from server.db import db, init_all_tables
from server.config import settings, IS_DATABRICKS_APP

# Import route modules
from server.routes import (
    conflict,
    maritime,
    military,
    seismology,
    climate,
    wildfire,
    news,
    market,
    economic,
    intelligence,
    infrastructure,
    cyber,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    print(f"[app] Starting World Monitor (Databricks App: {IS_DATABRICKS_APP})")
    print(f"[app] Demo mode: {settings.DEMO_MODE}")

    # Debug: Print database-related env vars
    print(f"[app] PGHOST={os.environ.get('PGHOST', '(not set)')}")
    print(f"[app] PGPORT={os.environ.get('PGPORT', '(not set)')}")
    print(f"[app] PGDATABASE={os.environ.get('PGDATABASE', '(not set)')}")
    print(f"[app] PGUSER={os.environ.get('PGUSER', '(not set)')}")
    print(f"[app] DATABRICKS_HOST={os.environ.get('DATABRICKS_HOST', '(not set)')}")
    print(f"[app] DATABRICKS_TOKEN={'(set)' if os.environ.get('DATABRICKS_TOKEN') else '(not set)'}")

    # Initialize database
    if settings.is_lakebase_configured():
        await db.get_pool()
        await init_all_tables()  # Creates all tables: cache, vessels, earthquakes, conflicts, fires, quotes
        await db.start_token_refresh_loop()
        print("[app] Lakebase connected with all tables initialized")
    else:
        print("[app] Running in demo mode (no database)")

    yield

    # Shutdown
    await db.close()
    print("[app] Shutdown complete")


app = FastAPI(
    title="World Monitor",
    description="Real-Time Global Intelligence Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8000",  # FastAPI dev
        "https://*.databricksapps.com",  # Databricks Apps
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "databricks_app": IS_DATABRICKS_APP,
        "demo_mode": settings.DEMO_MODE,
        "database": "connected" if not db.is_demo_mode else "demo",
    }


# Debug endpoint to check paths
@app.get("/api/debug/paths")
async def debug_paths():
    """Debug endpoint to check file paths."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    def list_dir_safe(path):
        try:
            if os.path.exists(path):
                contents = os.listdir(path)
                return contents[:20] if len(contents) > 20 else contents  # Limit to 20 items
            return "NOT_EXISTS"
        except Exception as e:
            return str(e)

    frontend_dist_cwd = os.path.join(cwd, "frontend", "dist")
    frontend_dist_base = os.path.join(base_dir, "frontend", "dist")

    # Get relevant env vars
    env_vars = {
        k: v for k, v in os.environ.items()
        if any(x in k.upper() for x in ["DATABRICKS", "APP", "SOURCE", "PATH"])
    }

    return {
        "cwd": cwd,
        "base_dir": base_dir,
        "__file__": __file__,
        "cwd_contents": list_dir_safe(cwd),
        "base_dir_contents": list_dir_safe(base_dir),
        "frontend_exists_cwd": os.path.exists(os.path.join(cwd, "frontend")),
        "frontend_exists_base": os.path.exists(os.path.join(base_dir, "frontend")),
        "frontend_contents_cwd": list_dir_safe(os.path.join(cwd, "frontend")),
        "frontend_contents_base": list_dir_safe(os.path.join(base_dir, "frontend")),
        "frontend_dist_exists_cwd": os.path.exists(frontend_dist_cwd),
        "frontend_dist_exists_base": os.path.exists(frontend_dist_base),
        "frontend_dist_contents_cwd": list_dir_safe(frontend_dist_cwd),
        "frontend_dist_contents_base": list_dir_safe(frontend_dist_base),
        "index_html_exists_cwd": os.path.exists(os.path.join(frontend_dist_cwd, "index.html")),
        "index_html_exists_base": os.path.exists(os.path.join(frontend_dist_base, "index.html")),
        "relevant_env_vars": env_vars,
        "frontend_cache": _frontend_dir_cache,
    }


# Version endpoint
@app.get("/api/version")
async def get_version():
    """Return application version info."""
    return {
        "version": "1.0.0",
        "platform": "databricks-apps",
        "features": {
            "lakebase": settings.is_lakebase_configured(),
            "foundation_models": bool(settings.SERVING_ENDPOINT),
        }
    }


# Register API routers with versioned prefixes
app.include_router(conflict.router, prefix="/api/conflict/v1", tags=["Conflict"])
app.include_router(maritime.router, prefix="/api/maritime/v1", tags=["Maritime"])
app.include_router(military.router, prefix="/api/military/v1", tags=["Military"])
app.include_router(seismology.router, prefix="/api/seismology/v1", tags=["Seismology"])
app.include_router(climate.router, prefix="/api/climate/v1", tags=["Climate"])
app.include_router(wildfire.router, prefix="/api/wildfire/v1", tags=["Wildfire"])
app.include_router(news.router, prefix="/api/news/v1", tags=["News"])
app.include_router(market.router, prefix="/api/market/v1", tags=["Market"])
app.include_router(economic.router, prefix="/api/economic/v1", tags=["Economic"])

# Also register at /api for frontend compatibility (without version prefix)
app.include_router(conflict.router, prefix="/api", tags=["Conflict-Compat"])
app.include_router(maritime.router, prefix="/api", tags=["Maritime-Compat"])
app.include_router(military.router, prefix="/api", tags=["Military-Compat"])
app.include_router(seismology.router, prefix="/api", tags=["Seismology-Compat"])
app.include_router(climate.router, prefix="/api", tags=["Climate-Compat"])
app.include_router(wildfire.router, prefix="/api", tags=["Wildfire-Compat"])
app.include_router(news.router, prefix="/api", tags=["News-Compat"])
app.include_router(market.router, prefix="/api", tags=["Market-Compat"])
app.include_router(economic.router, prefix="/api", tags=["Economic-Compat"])
app.include_router(intelligence.router, prefix="/api", tags=["Intelligence-Compat"])
app.include_router(infrastructure.router, prefix="/api", tags=["Infrastructure-Compat"])
app.include_router(cyber.router, prefix="/api", tags=["Cyber-Compat"])
app.include_router(intelligence.router, prefix="/api/intelligence/v1", tags=["Intelligence"])
app.include_router(infrastructure.router, prefix="/api/infrastructure/v1", tags=["Infrastructure"])
app.include_router(cyber.router, prefix="/api/cyber/v1", tags=["Cyber"])


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    print(f"[error] {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Serve React frontend (production)
# Cache for frontend directory path (lazy initialization)
_frontend_dir_cache = {"path": None, "checked": False}


def find_frontend_dir():
    """Find the frontend dist directory (with caching)."""
    if _frontend_dir_cache["checked"]:
        return _frontend_dir_cache["path"]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    # Get DATABRICKS_APP_NAME env var to detect if running in Databricks Apps
    app_name = os.environ.get("DATABRICKS_APP_NAME", "")
    print(f"[app] DATABRICKS_APP_NAME={app_name}")

    possible_paths = [
        os.path.join(cwd, "frontend", "dist"),  # CWD-relative (Databricks Apps)
        os.path.join(base_dir, "frontend", "dist"),  # __file__-relative
        os.path.join(base_dir, "..", "frontend", "dist"),
        "/app/frontend/dist",
        "/databricks/src/frontend/dist",
        "frontend/dist",
    ]

    # Also check environment for any hints about source location
    for env_key in ["DATABRICKS_SOURCE_PATH", "SOURCE_PATH", "APP_SOURCE_PATH"]:
        if env_val := os.environ.get(env_key):
            possible_paths.insert(0, os.path.join(env_val, "frontend", "dist"))
            print(f"[app] Added path from {env_key}: {env_val}")

    print(f"[app] Looking for frontend. CWD: {cwd}, base_dir: {base_dir}")
    print(f"[app] __file__ = {__file__}")

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        index_path = os.path.join(abs_path, "index.html")
        exists = os.path.exists(abs_path)
        is_dir = os.path.isdir(abs_path) if exists else False
        index_exists = os.path.exists(index_path) if exists else False
        print(f"[app] Checking: {abs_path} -> exists={exists}, isdir={is_dir}, index={index_exists}")
        if exists and is_dir and index_exists:
            print(f"[app] SUCCESS: Found frontend at: {abs_path}")
            _frontend_dir_cache["path"] = abs_path
            _frontend_dir_cache["checked"] = True
            return abs_path

    print(f"[app] FAILED: Frontend not found after checking all paths")

    # Debug: list directory contents to help diagnose
    try:
        print(f"[app] DEBUG CWD contents: {os.listdir(cwd)}")
        if os.path.exists(os.path.join(cwd, "frontend")):
            print(f"[app] DEBUG frontend/ contents: {os.listdir(os.path.join(cwd, 'frontend'))}")
            if os.path.exists(os.path.join(cwd, "frontend", "dist")):
                print(f"[app] DEBUG frontend/dist/ contents: {os.listdir(os.path.join(cwd, 'frontend', 'dist'))}")
        # Also check base_dir
        if base_dir != cwd:
            print(f"[app] DEBUG base_dir contents: {os.listdir(base_dir)}")
    except Exception as e:
        print(f"[app] Error listing dirs: {e}")

    _frontend_dir_cache["checked"] = True
    return None


# Mount assets directory if it exists at startup
def mount_assets_if_exists():
    """Try to mount assets directory."""
    frontend_dir = find_frontend_dir()
    if frontend_dir:
        assets_dir = os.path.join(frontend_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
            print(f"[app] Mounted assets from: {assets_dir}")
            return True
    return False


# Try mounting at import time (may fail, will retry at request time)
try:
    mount_assets_if_exists()
except Exception as e:
    print(f"[app] Could not mount assets at startup: {e}")


# SPA fallback - always define this route, check path at request time
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React SPA for all non-API routes."""
    # Don't serve index.html for API routes
    if full_path.startswith("api/"):
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"},
        )

    # Find frontend directory (lazy, cached)
    frontend_dir = find_frontend_dir()

    if frontend_dir:
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

    return JSONResponse(
        status_code=404,
        content={
            "message": "World Monitor API",
            "docs": "/docs",
            "health": "/api/health",
            "note": "Frontend not built or not found. Run: cd frontend && npm run build"
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
