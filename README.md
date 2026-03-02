# World Monitor - Databricks App

Real-Time Global Intelligence Dashboard running on Databricks Apps with Delta Lake persistence.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Databricks Apps                     │
├─────────────────────────────────────────────────────┤
│  React Frontend ─────▶ FastAPI Backend              │
│  (MapLibre/Deck.gl)     (Python 3.11+)              │
│                              │                       │
│                              ▼                       │
│  ┌─────────────┐    ┌─────────────────────┐        │
│  │  Lakebase   │    │   Delta Lake Tables  │        │
│  │ (PostgreSQL)│    │   - conflicts        │        │
│  │  - cache    │    │   - vessels          │        │
│  │  - sessions │    │   - earthquakes      │        │
│  └─────────────┘    │   - news             │        │
│                     │   - market           │        │
│                     └─────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)
- Databricks CLI 0.229.0+

### Local Development

```bash
# Backend
cd worldmonitor-databricks
uv sync
export DATABRICKS_PROFILE=your-profile
uv run uvicorn app:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev  # Runs on port 5173
```

### Deployment to Databricks

```bash
# 1. Create the app
databricks apps create worldmonitor --description "Global Intelligence Dashboard" -p your-profile

# 2. Build frontend
cd frontend && npm run build && cd ..

# 3. Sync files (excluding node_modules)
databricks sync . /Workspace/Users/you@example.com/worldmonitor \
  --exclude node_modules \
  --exclude .venv \
  --exclude __pycache__ \
  -p your-profile

# 4. Deploy
databricks apps deploy worldmonitor \
  --source-code-path /Workspace/Users/you@example.com/worldmonitor \
  -p your-profile

# 5. Add resources via UI:
#    - Database: Lakebase instance
#    - Model serving: databricks-claude-sonnet-4-5
```

## API Endpoints

| Domain | Endpoints | Description |
|--------|-----------|-------------|
| `/api/conflict/v1` | ACLED, UCDP events | Conflict data |
| `/api/maritime/v1` | AIS vessels | Ship tracking |
| `/api/military/v1` | Flights, bases | Military tracking |
| `/api/seismology/v1` | USGS earthquakes | Seismic events |
| `/api/climate/v1` | Anomalies | Climate data |
| `/api/wildfire/v1` | FIRMS fires | Satellite fires |
| `/api/news/v1` | RSS digest | News aggregation |
| `/api/market/v1` | Quotes, crypto | Market data |
| `/api/economic/v1` | FRED, World Bank | Economic indicators |
| `/api/intelligence/v1` | Risk scores | AI analysis |
| `/api/infrastructure/v1` | Outages | Infrastructure status |
| `/api/cyber/v1` | Threats | Cyber IOCs |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PGHOST` | Auto | Lakebase host (from resource) |
| `PGDATABASE` | Auto | Lakebase database (from resource) |
| `SERVING_ENDPOINT` | No | Foundation Model endpoint |
| `ACLED_ACCESS_TOKEN` | No | ACLED API key |
| `FINNHUB_API_KEY` | No | Finnhub API key |
| `NASA_FIRMS_API_KEY` | No | NASA FIRMS key |
| `FRED_API_KEY` | No | FRED API key |

## Delta Lake Tables

| Table | Data Source | Update Frequency |
|-------|-------------|------------------|
| `worldmonitor.conflicts_acled` | ACLED API | Daily |
| `worldmonitor.conflicts_ucdp` | UCDP API | Daily |
| `worldmonitor.earthquakes` | USGS | Real-time |
| `worldmonitor.fires_satellite` | NASA FIRMS | 6-hourly |
| `worldmonitor.news_articles` | RSS feeds | 15-minute |
| `worldmonitor.market_quotes` | Finnhub/CoinGecko | 1-minute |

## Monitoring

Access application logs at: `https://your-app-url/logz`

## License

Based on World Monitor (AGPL-3.0) - https://github.com/koala73/worldmonitor
