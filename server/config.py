"""
Dual-mode authentication configuration for World Monitor.
Handles both local development and Databricks Apps deployment.
"""

import os
from functools import lru_cache
from databricks.sdk import WorkspaceClient

# Detect environment
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    """Get authenticated WorkspaceClient.

    In Databricks Apps: Uses auto-injected service principal credentials.
    Locally: Uses Databricks CLI profile from environment.
    """
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    else:
        profile = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
        return WorkspaceClient(profile=profile)


def get_oauth_token() -> str:
    """Get OAuth token for Lakebase/API authentication.

    Uses the SDK's authenticate() method which returns proper tokens
    for both OAuth and PAT authentication modes.
    Returns empty string if token cannot be obtained (graceful fallback).
    """
    try:
        client = get_workspace_client()
        auth_headers = client.config.authenticate()
        if auth_headers and "Authorization" in auth_headers:
            return auth_headers["Authorization"].replace("Bearer ", "")
        print("[config] WARNING: No Authorization header in auth response")
        return ""
    except Exception as e:
        print(f"[config] ERROR: Failed to obtain OAuth token: {e}")
        return ""


def get_workspace_host() -> str:
    """Get workspace host URL with https:// prefix.

    IMPORTANT: DATABRICKS_HOST in Databricks Apps is just hostname without scheme.
    """
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    client = get_workspace_client()
    return client.config.host  # SDK includes https://


def _safe_int(value: str, default: int) -> int:
    """Safely convert string to int with fallback."""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


class Settings:
    """Application settings loaded from environment."""

    # Database
    PGHOST: str = os.environ.get("PGHOST", "")
    PGPORT: int = _safe_int(os.environ.get("PGPORT", ""), 5432)
    PGDATABASE: str = os.environ.get("PGDATABASE", "")
    PGUSER: str = os.environ.get("PGUSER", "")

    # AI/LLM
    SERVING_ENDPOINT: str = os.environ.get("SERVING_ENDPOINT", "databricks-claude-sonnet-4-5")

    # External APIs
    # ACLED OAuth credentials (new authentication system as of Sept 2025)
    ACLED_EMAIL: str = os.environ.get("ACLED_EMAIL", "")
    ACLED_PASSWORD: str = os.environ.get("ACLED_PASSWORD", "")
    FINNHUB_API_KEY: str = os.environ.get("FINNHUB_API_KEY", "")
    NASA_FIRMS_API_KEY: str = os.environ.get("NASA_FIRMS_API_KEY", "")
    FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "")
    UCDP_ACCESS_TOKEN: str = os.environ.get("UCDP_ACCESS_TOKEN", "")
    CLOUDFLARE_API_TOKEN: str = os.environ.get("CLOUDFLARE_API_TOKEN", "")

    # Feature flags
    DEMO_MODE: bool = not bool(os.environ.get("PGHOST"))

    @classmethod
    def is_lakebase_configured(cls) -> bool:
        """Check if Lakebase database is configured."""
        return bool(cls.PGHOST and cls.PGDATABASE)


settings = Settings()
