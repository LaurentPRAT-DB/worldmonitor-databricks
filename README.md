# World Monitor

Real-Time Global Intelligence Dashboard running on Databricks Apps with Delta Lake persistence and AI-powered analysis.

![Platform](https://img.shields.io/badge/platform-Databricks%20Apps-orange)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![React](https://img.shields.io/badge/react-18+-61DAFB)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)

## Overview

World Monitor aggregates data from 15+ global data sources to provide real-time geopolitical intelligence on a unified dashboard. Built on Databricks Apps with FastAPI backend and React frontend, featuring AI-powered analysis via Foundation Models.

### Key Features

- **Real-time Conflict Tracking** - ACLED & UCDP armed conflict events
- **Seismic Activity** - USGS earthquake data with magnitude filtering
- **Wildfire Detection** - NASA FIRMS satellite fire data
- **Maritime Tracking** - AIS vessel positions and historical routes
- **Military Activity** - Aircraft tracking via ADS-B
- **Financial Markets** - Stock indices, crypto prices
- **AI Intelligence** - Claude Sonnet 4.5 powered analysis and chat
- **Country Risk Scores** - Multi-factor risk assessment

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Databricks Apps                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐         ┌─────────────────────────────────┐ │
│  │  React Frontend │         │      FastAPI Backend            │ │
│  │  (MapLibre GL)  │ ──────▶ │      (Python 3.11+)             │ │
│  │  - Map View     │         │                                 │ │
│  │  - Stats Panel  │         │  12 API Modules:                │ │
│  │  - Intel Panel  │         │  • conflict   • maritime        │ │
│  │  - Events Feed  │         │  • seismology • military        │ │
│  └─────────────────┘         │  • wildfire   • market          │ │
│                              │  • climate    • economic        │ │
│                              │  • news       • intelligence    │ │
│                              │  • cyber      • infrastructure  │ │
│                              └───────────────┬─────────────────┘ │
│                                              │                    │
│        ┌─────────────────────────────────────┼──────────────────┐│
│        │                                     ▼                  ││
│        │  ┌─────────────┐    ┌─────────────────────────────┐   ││
│        │  │  Lakebase   │    │     Unity Catalog           │   ││
│        │  │ (PostgreSQL)│    │     Delta Lake Tables       │   ││
│        │  │             │    │                             │   ││
│        │  │ • Cache     │    │  Raw Tables:                │   ││
│        │  │ • Sessions  │    │  • conflict_events          │   ││
│        │  │ • Real-time │    │  • earthquake_events        │   ││
│        │  │   positions │    │  • wildfire_events          │   ││
│        │  └─────────────┘    │  • maritime_vessels         │   ││
│        │                     │  • market_quotes            │   ││
│        │                     │                             │   ││
│        │  ┌─────────────────────────────────────────────────┐  ││
│        │  │         Foundation Model API                    │  ││
│        │  │         (Claude Sonnet 4.5)                     │  ││
│        │  │  • Country Briefs • Ask AI Chat                 │  ││
│        │  └─────────────────────────────────────────────────┘  ││
│        └────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| uv | latest | Python package manager |
| Databricks CLI | 0.229.0+ | Deployment |

### Installation

```bash
# Clone repository
git clone https://github.com/LaurentPRAT-DB/worldmonitor-databricks.git
cd worldmonitor-databricks

# Backend setup
uv sync

# Frontend setup
cd frontend
npm install
npm run build
cd ..
```

### Local Development

```bash
# Terminal 1: Backend (port 8000)
export DATABRICKS_PROFILE=your-profile
uv run uvicorn app:app --reload --port 8000

# Terminal 2: Frontend dev server (port 5173)
cd frontend
npm run dev
```

Open http://localhost:5173 for the dashboard.

### Deployment to Databricks Apps

```bash
# 1. Build frontend
cd frontend && npm run build && cd ..

# 2. Deploy using DABs
databricks bundle deploy -t dev --profile YOUR_PROFILE

# 3. Start the app
databricks apps deploy worldmonitor-dev \
  --source-code-path /Workspace/Users/you@example.com/.bundle/worldmonitor/dev/files \
  --profile YOUR_PROFILE
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| **Database (auto-injected)** | | |
| `PGHOST` | Auto | Lakebase host |
| `PGPORT` | Auto | Lakebase port |
| `PGDATABASE` | Auto | Lakebase database |
| `PGUSER` | Auto | Lakebase user |
| **AI & Analytics** | | |
| `SERVING_ENDPOINT` | No | Foundation Model (default: `databricks-claude-sonnet-4-5`) |
| `DATABRICKS_WAREHOUSE_ID` | No | SQL Warehouse for UC queries |
| **External APIs** | | |
| `FINNHUB_API_KEY` | Yes | Stock market data |
| `FRED_API_KEY` | Yes | Economic indicators |
| `NASA_FIRMS_API_KEY` | Yes | Wildfire detection |
| `UCDP_ACCESS_TOKEN` | Yes | Conflict data (Uppsala) |
| `ACLED_EMAIL` | No | ACLED API (OAuth) |
| `ACLED_PASSWORD` | No | ACLED API (OAuth) |

## API Endpoints

| Domain | Prefix | Key Endpoints |
|--------|--------|---------------|
| **Conflict** | `/api/conflict/v1` | `GET /list-acled-events`, `GET /list-ucdp-events` |
| **Seismology** | `/api/seismology/v1` | `GET /list-earthquakes` |
| **Wildfire** | `/api/wildfire/v1` | `GET /list-fires` |
| **Maritime** | `/api/maritime/v1` | `GET /list-vessels`, `GET /vessel-route/{mmsi}` |
| **Military** | `/api/military/v1` | `GET /list-flights`, `GET /list-bases` |
| **Market** | `/api/market/v1` | `GET /quotes`, `GET /crypto` |
| **Intelligence** | `/api/intelligence/v1` | `GET /risk-scores`, `GET /country-brief/{code}`, `POST /ask` |
| **Infrastructure** | `/api/infrastructure/v1` | `GET /outages` |
| **Cyber** | `/api/cyber/v1` | `GET /threats` |

### Ask AI Example

```bash
curl -X POST "https://your-app.databricksapps.com/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the current geopolitical hotspots?"}'
```

See [docs/API.md](docs/API.md) for complete API documentation.

## Data Sources

| Source | Data Type | Update Frequency | API Key |
|--------|-----------|------------------|---------|
| [USGS](https://earthquake.usgs.gov/) | Earthquakes | Real-time | No |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Wildfires | 6-hourly | Yes |
| [ACLED](https://acleddata.com/) | Armed Conflicts | Daily | Yes |
| [UCDP](https://ucdp.uu.se/) | Conflict Fatalities | Historical | Yes |
| [Finnhub](https://finnhub.io/) | Stock Quotes | Real-time | Yes |
| [CoinGecko](https://www.coingecko.com/) | Crypto Prices | Real-time | No |
| [FRED](https://fred.stlouisfed.org/) | Economic Data | Daily | Yes |
| [Open-Meteo](https://open-meteo.com/) | Climate | Hourly | No |

## Delta Lake Tables

| Table | Description | Partition |
|-------|-------------|-----------|
| `conflict_events` | ACLED/UCDP events | `event_date` |
| `earthquake_events` | USGS seismic | `time` |
| `wildfire_events` | NASA FIRMS fires | `acq_date` |
| `maritime_vessels` | AIS positions | `timestamp` |
| `market_quotes` | Financial data | `timestamp` |
| `country_risk_scores` | Risk scores | `calculated_at` |

See [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for complete schema documentation.

## Project Structure

```
worldmonitor-databricks/
├── app.py                 # FastAPI entry point
├── app.yaml               # Databricks Apps config
├── databricks.yml         # DABs bundle config
├── requirements.txt       # Python dependencies
│
├── server/                # Backend modules
│   ├── config.py          # Settings & auth
│   ├── db.py              # Lakebase connection
│   ├── llm.py             # Foundation Model client
│   ├── delta_tables.py    # Delta Lake schemas
│   └── routes/            # API endpoints (12 modules)
│
├── frontend/              # React application
│   ├── src/
│   │   ├── App.tsx
│   │   ├── stores/        # Zustand state
│   │   └── components/    # UI components
│   └── dist/              # Production build
│
├── notebooks/             # Databricks notebooks
│   ├── archive_earthquakes.py
│   ├── archive_conflicts.py
│   ├── archive_fires.py
│   ├── archive_market_quotes.py
│   ├── archive_vessel_positions.py
│   └── sync_vessel_history_to_lakebase.py
│
├── resources/             # DABs resources
│   ├── worldmonitor_app.yml
│   └── archival_jobs.yml
│
└── docs/                  # Documentation
    ├── API.md
    └── DATA_DICTIONARY.md
```

## Data Architecture

### Hybrid Storage Strategy

World Monitor uses a two-tier storage architecture:

| Tier | Technology | Purpose | Retention |
|------|------------|---------|-----------|
| **Hot** | Lakebase (PostgreSQL) | Real-time UI interactions, caching | Hours to days |
| **Cold** | Unity Catalog (Delta Lake) | Long-term analytics, historical queries | Indefinite |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   External APIs  ──▶  FastAPI Backend  ──▶  Lakebase (Hot)              │
│   (USGS, ACLED,        (fetch & save)       (PostgreSQL)                │
│    NASA, etc.)                                   │                       │
│                                                  │ Archive Jobs          │
│                                                  │ (daily/hourly)        │
│                                                  ▼                       │
│                                           Unity Catalog (Cold)          │
│                                           (Delta Lake Tables)           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Lakebase Tables (Hot Storage)

| Table | Retention | Purpose |
|-------|-----------|---------|
| `api_cache` | TTL-based | API response caching |
| `vessel_positions` | 24 hours | Real-time vessel tracking |
| `earthquakes` | 30 days | USGS earthquake data |
| `conflict_events` | 30 days | ACLED/UCDP conflict data |
| `fire_detections` | 7 days | NASA FIRMS wildfire data |
| `market_quotes_history` | 24 hours | Finnhub/CoinGecko quotes |

### Unity Catalog Tables (Cold Storage)

| Table | Source | Partition Key |
|-------|--------|---------------|
| `earthquake_events` | earthquakes | `time` |
| `conflict_events` | conflict_events | `event_date` |
| `wildfire_events` | fire_detections | `acq_date` |
| `vessel_positions_history` | vessel_positions | `timestamp` |
| `market_quotes` | market_quotes_history | `timestamp` |

**Catalog**: `serverless_stable_3n0ihb_catalog`
**Schema**: `worldmonitor_dev`

## Databricks Jobs

### Archival Jobs (Lakebase → Unity Catalog)

These jobs move old data from Lakebase to Unity Catalog for cost-effective long-term storage.

| Job Name | Schedule | Data Archived |
|----------|----------|---------------|
| `[dev] World Monitor - Lakebase Archival` | Daily at 2 AM UTC | Earthquakes (30d), Conflicts (30d), Fires (7d), Vessels (24h) |
| `[dev] World Monitor - Market Quotes Archival (Hourly)` | Hourly | Market quotes (24h) |

**Archival Process:**
1. **Read** old records from Lakebase (older than retention threshold)
2. **MERGE** into Unity Catalog Delta table (avoids duplicates via `event_id`)
3. **DELETE** archived records from Lakebase to keep it lean

### Job Management

```bash
# Deploy all jobs
databricks bundle deploy -t dev --profile FEVM_SERVERLESS_STABLE

# List jobs
databricks jobs list --profile FEVM_SERVERLESS_STABLE | grep worldmonitor

# Enable archival job (replace <job_id>)
databricks jobs update <job_id> --json '{"settings":{"schedule":{"pause_status":"UNPAUSED"}}}' \
  --profile FEVM_SERVERLESS_STABLE

# Run job manually
databricks jobs run-now <job_id> --profile FEVM_SERVERLESS_STABLE

# Check job run status
databricks jobs get-run <run_id> --profile FEVM_SERVERLESS_STABLE
```

## Administration & Monitoring

### Quick Health Check

```bash
# Set your profile
export DATABRICKS_PROFILE=FEVM_SERVERLESS_STABLE
export APP_URL=https://worldmonitor-dev-7474645572615955.aws.databricksapps.com

# Get auth token
TOKEN=$(databricks auth token --profile $DATABRICKS_PROFILE)

# Health check
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/health" | jq
# Expected: {"status":"ok","database":"connected","demo_mode":false}

# Debug endpoint (detailed)
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/debug/lakebase" | jq
```

### Key Monitoring Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /api/health` | Overall app health | `{"status":"ok","database":"connected"}` |
| `GET /api/debug/lakebase` | Lakebase table counts | Row counts for all tables |
| `GET /api/version` | App version info | Version and build info |

### Watchpoints Checklist

#### 1. Application Health

| Check | Command | Expected |
|-------|---------|----------|
| App Status | `databricks apps get worldmonitor-dev --profile $DATABRICKS_PROFILE` | `state: RUNNING` |
| App Logs | `databricks apps logs worldmonitor-dev --profile $DATABRICKS_PROFILE` | No ERROR lines |
| Health Endpoint | `curl $APP_URL/api/health` | `"database": "connected"` |

#### 2. Lakebase Data Freshness

| Table | Check | Alert If |
|-------|-------|----------|
| `earthquakes` | `SELECT MAX(recorded_at) FROM earthquakes` | > 1 hour old |
| `vessel_positions` | `SELECT COUNT(*) FROM vessel_positions` | < 100 records |
| `conflict_events` | `SELECT MAX(recorded_at) FROM conflict_events` | > 24 hours old |
| `fire_detections` | `SELECT MAX(recorded_at) FROM fire_detections` | > 6 hours old |
| `market_quotes_history` | `SELECT MAX(recorded_at) FROM market_quotes_history` | > 5 minutes old |

```bash
# Check via debug endpoint
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/debug/lakebase" | jq '.table_counts'
```

#### 3. Unity Catalog Archival

| Check | SQL Query |
|-------|-----------|
| Earthquake archive size | `SELECT COUNT(*) FROM serverless_stable_3n0ihb_catalog.worldmonitor_dev.earthquake_events` |
| Conflict archive size | `SELECT COUNT(*) FROM serverless_stable_3n0ihb_catalog.worldmonitor_dev.conflict_events` |
| Latest archival | `SELECT MAX(ingested_at) FROM serverless_stable_3n0ihb_catalog.worldmonitor_dev.earthquake_events` |

#### 4. Job Health

```bash
# List recent job runs
databricks jobs list-runs --job-id <archival_job_id> --limit 5 --profile $DATABRICKS_PROFILE

# Check for failed runs
databricks jobs list-runs --job-id <archival_job_id> --profile $DATABRICKS_PROFILE | grep -i failed
```

| Job | Expected Frequency | Alert If |
|-----|-------------------|----------|
| Lakebase Archival | Daily 2 AM UTC | No SUCCESS in 48h |
| Market Quotes Archival | Hourly | No SUCCESS in 3h |

#### 5. External API Status

| API | Test Endpoint | Check |
|-----|---------------|-------|
| USGS | `/api/seismology/v1/list-earthquakes` | Returns data |
| NASA FIRMS | `/api/wildfire/v1/list-fires` | Returns data (requires API key) |
| Finnhub | `/api/market/v1/quotes` | Returns stock quotes |
| CoinGecko | `/api/market/v1/crypto` | Returns crypto prices |
| UCDP | `/api/conflict/v1/list-ucdp-events` | Returns conflict events |

```bash
# Test critical endpoints
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/seismology/v1/list-earthquakes?limit=1" | jq '.earthquakes | length'
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/market/v1/quotes" | jq '.quotes | length'
```

### Common Operations

#### Redeploy Application

```bash
cd frontend && npm run build && cd ..
databricks bundle deploy -t dev --profile FEVM_SERVERLESS_STABLE
databricks bundle run worldmonitor_app -t dev --profile FEVM_SERVERLESS_STABLE
```

#### Force Data Refresh

```bash
# Bypass cache for specific endpoints
curl -H "Authorization: Bearer $TOKEN" "$APP_URL/api/seismology/v1/list-earthquakes?force_refresh=true"
curl -H "Authorization: Bearer $TOKEN" "$APP_URL/api/conflict/v1/list-ucdp-events?force_refresh=true"
```

#### Run Archival Job Manually

```bash
# Get job ID
JOB_ID=$(databricks jobs list --profile $DATABRICKS_PROFILE --output json | jq -r '.jobs[] | select(.settings.name | contains("Lakebase Archival")) | .job_id')

# Trigger run
databricks jobs run-now $JOB_ID --profile $DATABRICKS_PROFILE
```

#### Check Lakebase Connection

```bash
# From app logs
databricks apps logs worldmonitor-dev --profile $DATABRICKS_PROFILE | grep -i "lakebase\|postgres\|database"
```

### Alerting Recommendations

| Metric | Warning | Critical |
|--------|---------|----------|
| App health endpoint | Response time > 5s | Returns error or demo_mode: true |
| Earthquake data age | > 2 hours | > 6 hours |
| Market quotes age | > 10 minutes | > 30 minutes |
| Daily archival job | Missed 1 run | Missed 2 consecutive runs |
| Lakebase row count | < 50% of expected | Table empty |

### Log Analysis

```bash
# View recent logs
databricks apps logs worldmonitor-dev --profile $DATABRICKS_PROFILE

# Filter for errors
databricks apps logs worldmonitor-dev --profile $DATABRICKS_PROFILE | grep -i "error\|exception\|failed"

# Filter for Lakebase issues
databricks apps logs worldmonitor-dev --profile $DATABRICKS_PROFILE | grep -i "lakebase\|postgres\|connection"
```

## Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Frontend not loading | Blank page, 404 | Run `npm run build`, redeploy |
| Lakebase connection failed | `demo_mode: true` in health | Check SDK version (≥0.81.0), verify IAM roles |
| UCDP returns empty | No conflict events | Date range must be recent; check `UCDP_ACCESS_TOKEN` |
| Fire markers missing | No fires on map | Verify `NASA_FIRMS_API_KEY` in app.yaml |
| Archival job fails | Job status FAILED | Check notebook logs, verify Lakebase credentials |
| Stale data | Old timestamps | Run `force_refresh=true` or check external API status |
| High latency | Slow API responses | Check Lakebase connection pool, review query performance |
| Market quotes empty | No stock/crypto data | Verify `FINNHUB_API_KEY`, check rate limits |

### Lakebase Authentication Issues

If the app shows `demo_mode: true`:

1. **Check SDK version**: Must be `databricks-sdk>=0.81.0`
2. **Verify IAM role exists** for service principal:
   ```bash
   databricks lakebase list-roles --project worldmonitor-cache --profile $DATABRICKS_PROFILE
   ```
3. **Test credential generation**:
   ```python
   from databricks.sdk import WorkspaceClient
   w = WorkspaceClient()
   cred = w.postgres.generate_database_credential(
       endpoint="projects/worldmonitor-cache/branches/production/endpoints/primary"
   )
   print(cred.token[:20] + "...")  # Should print partial token
   ```

## License

Based on [World Monitor](https://github.com/koala73/worldmonitor) - AGPL-3.0

## Acknowledgments

- Original World Monitor by koala73
- Databricks Apps platform
- Claude Sonnet 4.5 via Databricks Foundation Models
- Data: USGS, NASA, ACLED, UCDP, Finnhub, FRED
