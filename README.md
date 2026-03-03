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
├── resources/             # DABs resources
│   └── worldmonitor_app.yml
│
└── docs/                  # Documentation
    ├── API.md
    └── DATA_DICTIONARY.md
```

## Monitoring

- **Logs**: `https://your-app-url/logz`
- **Health**: `GET /api/health`
- **Version**: `GET /api/version`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Frontend not loading | Run `npm run build`, redeploy |
| Lakebase connection failed | Check resource binding in app.yaml |
| UCDP returns empty | Date range must be 2019-2023 (historical data) |
| Fire markers missing | Verify NASA FIRMS API key |

## License

Based on [World Monitor](https://github.com/koala73/worldmonitor) - AGPL-3.0

## Acknowledgments

- Original World Monitor by koala73
- Databricks Apps platform
- Claude Sonnet 4.5 via Databricks Foundation Models
- Data: USGS, NASA, ACLED, UCDP, Finnhub, FRED
