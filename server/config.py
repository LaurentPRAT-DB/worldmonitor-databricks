"""
Dual-mode authentication configuration for World Monitor.
Handles both local development and Databricks Apps deployment.
"""

import os
from functools import lru_cache
from databricks.sdk import WorkspaceClient

# Detect environment
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# Lakebase Autoscaling endpoint (for generating database credentials)
LAKEBASE_ENDPOINT = "projects/worldmonitor-cache/branches/production/endpoints/primary"


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
    """Get OAuth token for general API authentication (Foundation Models, etc).

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


def get_lakebase_credential() -> str:
    """Get database credential for Lakebase Autoscaling authentication.

    For Lakebase Autoscaling, we must use postgres.generate_database_credential()
    instead of the generic workspace OAuth token. This returns a short-lived
    token (1 hour) specifically for PostgreSQL authentication.

    Returns empty string if credential cannot be obtained (graceful fallback).
    """
    try:
        client = get_workspace_client()
        cred = client.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT)
        if cred and cred.token:
            print(f"[config] Generated Lakebase credential for endpoint: {LAKEBASE_ENDPOINT}")
            return cred.token
        print("[config] WARNING: No token in database credential response")
        return ""
    except Exception as e:
        print(f"[config] ERROR: Failed to generate Lakebase credential: {e}")
        return ""


def get_current_user_email() -> str:
    """Get the current user's email for Lakebase Autoscaling authentication.

    Lakebase Autoscaling uses the user's email as the Postgres username.
    """
    try:
        client = get_workspace_client()
        user = client.current_user.me()
        return user.user_name
    except Exception as e:
        print(f"[config] ERROR: Failed to get current user: {e}")
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

    # Database (Lakebase Autoscaling)
    PGHOST: str = os.environ.get("PGHOST", "")
    PGPORT: int = _safe_int(os.environ.get("PGPORT", ""), 5432)
    PGDATABASE: str = os.environ.get("PGDATABASE", "databricks_postgres")
    _pguser: str = os.environ.get("PGUSER", "")

    @property
    def PGUSER(self) -> str:
        """Get Postgres user - falls back to authenticated user email for Lakebase Autoscaling."""
        if self._pguser:
            return self._pguser
        return get_current_user_email()

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
    # FORCE_DEMO_MODE: Set to "true" to force demo mode even if Lakebase is configured
    # FORCE_LAKEBASE: Set to "true" to force Lakebase connection (fail if unavailable)
    FORCE_DEMO_MODE: bool = os.environ.get("FORCE_DEMO_MODE", "").lower() in ("true", "1", "yes")
    FORCE_LAKEBASE: bool = os.environ.get("FORCE_LAKEBASE", "").lower() in ("true", "1", "yes")

    @property
    def DEMO_MODE(self) -> bool:
        """Check if running in demo mode (no database persistence)."""
        if self.FORCE_DEMO_MODE:
            return True
        if self.FORCE_LAKEBASE:
            return False
        # Default: demo mode if PGHOST is not configured
        return not bool(self.PGHOST)

    @classmethod
    def is_lakebase_configured(cls) -> bool:
        """Check if Lakebase database is configured."""
        return bool(cls.PGHOST and cls.PGDATABASE)


settings = Settings()
