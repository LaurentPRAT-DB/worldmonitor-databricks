# World Monitor Testing Documentation

Comprehensive testing guide for the World Monitor Databricks App.

## Test Environment

| Environment | URL | Authentication |
|-------------|-----|----------------|
| **Local Dev** | `http://localhost:8000` | Databricks Profile |
| **Deployed App** | `https://worldmonitor-dev-7474645572615955.aws.databricksapps.com` | Databricks OAuth |

## API Endpoint Test Results

### Test Date: 2026-03-04

| Category | Endpoint | Status | Notes |
|----------|----------|--------|-------|
| **System** | | | |
| | `GET /api/health` | ✅ Pass | Returns health status |
| | `GET /api/version` | ✅ Pass | Returns version info |
| **Seismology** | | | |
| | `GET /api/seismology/v1/list-earthquakes` | ✅ Pass | 168 earthquakes loaded |
| **Cyber** | | | |
| | `GET /api/cyber/v1/list-cyber-threats` | ✅ Pass | abuse.ch public download feeds |
| | `GET /api/cyber/v1/threat-stats` | ✅ Pass | 100 threats aggregated |
| **Maritime** | | | |
| | `GET /api/maritime/v1/list-vessels` | ✅ Pass | 40 vessels (synthetic data) |
| | `GET /api/maritime/v1/vessel-route/{mmsi}` | ✅ Pass | Historical routes from Unity Catalog Delta Lake |
| | `GET /api/maritime/v1/vessel-routes` | ✅ Pass | All vessel routes (30 days history) |
| **Intelligence** | | | |
| | `GET /api/intelligence/v1/risk-scores` | ✅ Pass | 14 country risk scores |
| | `GET /api/intelligence/v1/country-brief/{code}` | ✅ Pass | AI-generated briefs (Claude Sonnet 4.5) |
| | `POST /api/intelligence/v1/ask` | ✅ Pass | Foundation Model chat |
| **Market** | | | |
| | `GET /api/market/v1/quotes` | ✅ Pass | SPY, QQQ, DIA, IWM, VTI live data |
| | `GET /api/market/v1/crypto` | ✅ Pass | BTC, ETH, and more |
| **Wildfire** | | | |
| | `GET /api/wildfire/v1/list-fires` | ✅ Pass | 985 active fires (NASA FIRMS) |
| **Conflict** | | | |
| | `GET /api/conflict/v1/list-acled-events` | ❌ Needs OAuth | Requires ACLED email/password |
| | `GET /api/conflict/v1/list-ucdp-events` | ✅ Pass | Historical conflict data (2019-2023) |
| **Climate** | | | |
| | `GET /api/climate/v1/alerts` | ✅ Pass | Open-Meteo (no key needed) |
| **News** | | | |
| | `GET /api/news/v1/list-articles` | ✅ Pass | RSS feeds aggregated |
| **Economic** | | | |
| | `GET /api/economic/v1/indicators` | ✅ Pass | FRED economic data |
| **Military** | | | |
| | `GET /api/military/v1/list-military-flights` | ✅ Pass | Synthetic data (Persian Gulf focus) |
| | `GET /api/military/v1/list-military-bases` | ✅ Pass | 14 regional bases (US/Coalition, Iran) |
| | `GET /api/military/v1/theater-posture/{theater}` | ✅ Pass | Alert assessments (high for Persian Gulf) |
| **Infrastructure** | | | |
| | `GET /api/infrastructure/v1/outages` | ✅ Pass | Multi-source aggregation |

### Status Legend
- ✅ **Pass**: Endpoint working correctly in production
- ⚠️ **Rate Limited**: Works but may hit free tier limits
- ❌ **Needs OAuth**: Requires additional authentication setup

---

## Running Tests

### Local Testing

```bash
# Start local server
cd worldmonitor-databricks
export DATABRICKS_PROFILE=FEVM_SERVERLESS_STABLE
uv run uvicorn app:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/api/health

# Test earthquakes
curl "http://localhost:8000/api/seismology/v1/list-earthquakes?limit=5"

# Test cyber threats
curl "http://localhost:8000/api/cyber/v1/list-cyber-threats?limit=10"
```

### Frontend Testing

```bash
# Start frontend dev server
cd frontend
npm run dev

# Open browser to http://localhost:5173
# Use Chrome DevTools to inspect
```

### Integration Testing with Chrome DevTools MCP

```bash
# Navigate to app
mcp__chrome-devtools__navigate_page '{"type": "url", "url": "http://localhost:5173"}'

# Take screenshot
mcp__chrome-devtools__take_screenshot '{"filePath": "/tmp/worldmonitor.png"}'

# Check console errors
mcp__chrome-devtools__list_console_messages '{"types": ["error"]}'

# Get page snapshot for interaction testing
mcp__chrome-devtools__take_snapshot '{}'
```

---

## Test Cases

### TC-001: Dashboard Load
**Steps:**
1. Navigate to app URL
2. Wait for initial load

**Expected:**
- Map renders with default view
- Stats panel shows earthquake count, fire count, cyber threats
- No console errors

**Result:** ✅ Pass

### TC-002: Earthquake Data
**Steps:**
1. Open Data panel
2. Click "Earthquakes" tab
3. Verify data loads

**Expected:**
- Earthquake table shows recent events
- Magnitude, location, time displayed
- Map markers appear

**Result:** ✅ Pass

### TC-003: Cyber Threats
**Steps:**
1. Open Data panel
2. Click "Cyber" tab
3. Verify IOC data loads

**Expected:**
- IOC counts by type (URL, IP, Domain, Hash)
- Threat list with source attribution
- Filter functionality works

**Result:** ✅ Pass

### TC-004: Maritime Vessels
**Steps:**
1. Open Data panel
2. Click "Maritime" tab
3. Click on a vessel for route

**Expected:**
- Vessel list with positions
- Synthetic data clearly marked [DEMO]
- Route history available

**Result:** ✅ Pass (Synthetic mode)

### TC-005: AI Intelligence
**Steps:**
1. Open Intel panel
2. Select a country
3. Generate AI brief

**Expected:**
- Risk scores display
- AI-generated brief loads
- Chat functionality works

**Result:** ✅ Pass (requires Foundation Model access)

### TC-006: Map Interactions
**Steps:**
1. Click on map markers
2. Use zoom controls
3. Toggle data layers

**Expected:**
- Marker popups display event details
- Smooth zoom/pan
- Layer toggles work

**Result:** ✅ Pass

---

## Performance Benchmarks

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Initial page load | < 3s | ~2.5s | ✅ |
| API response (earthquakes) | < 500ms | ~300ms | ✅ |
| API response (cyber) | < 2s | ~1.5s | ✅ |
| Map render | < 1s | ~800ms | ✅ |
| AI brief generation | < 10s | ~5-8s | ✅ |

---

## Known Issues

### 1. ACLED OAuth Authentication
ACLED deprecated API key authentication in September 2025. Now requires OAuth:
- POST to `https://acleddata.com/oauth/token` with email/password
- Returns access_token valid for 24 hours
- Use Bearer token for API requests

**Status:** Code updated but credentials not configured. Set `ACLED_EMAIL` and `ACLED_PASSWORD` in app.yaml.

### 2. Rate Limiting
Free tier APIs have rate limits:
- **CoinGecko**: 10-50 calls/minute
- **OpenSky**: Limited without account
- **Finnhub**: 60 calls/minute

**Mitigation:** Caching implemented with 15-60 min TTL via Lakebase.

### 3. Synthetic Maritime Data
Real AIS data requires a paid subscription. Current implementation uses synthetic demo vessels with 30-day historical routes stored in Unity Catalog Delta Lake.

**Note:** Synthetic data is for demonstration purposes. Set `USE_SYNTHETIC_MARITIME_DATA=false` when real AIS feed is available.

### 4. UCDP Historical Data Only
UCDP (Uppsala Conflict Data Program) provides historical data from 2019-2023 only. Real-time conflict data requires ACLED.

### 5. Military Data is Synthetic
The Military section displays synthetic data focused on Persian Gulf / Strait of Hormuz region:
- **Aircraft**: Simulated flights (US Navy P-8, USAF RC-135/MQ-9, Iranian F-14/Su-35/drones, UAE/Saudi AEW)
- **Bases**: 14 real base locations (Al Udeid, NSA Bahrain, Al Dhafra, Bandar Abbas, Bushehr, Jask, etc.)
- **Theater Posture**: Elevated alert status for Strait of Hormuz reflecting Iran activity

**Note**: Real flight data would require OpenSky Network API integration.

---

## Deployment Verification Checklist

### Pre-Deployment
- [x] Frontend build successful (`npm run build`)
- [x] No TypeScript errors
- [x] All dependencies in requirements.txt
- [x] Environment variables configured in app.yaml
- [x] Lakebase resource binding configured

### Post-Deployment
- [x] App accessible at https://worldmonitor-dev-7474645572615955.aws.databricksapps.com
- [x] Health endpoint returns OK
- [x] Map loads with 700+ markers (earthquakes, fires, conflicts)
- [x] Stats panel shows live counts (168 earthquakes, 985 fires, 100 cyber threats)
- [x] Market data displays (SPY, QQQ, DIA, IWM, VTI with prices)
- [x] Maritime vessel routes load from Delta Lake (30 days history)
- [x] Vessel selection highlights route with glow effect
- [x] AI features work (Claude Sonnet 4.5 via Foundation Model API)
- [x] No console errors

### Security
- [x] No hardcoded credentials (all via env vars)
- [x] API keys stored in app.yaml environment variables
- [x] Lakebase connection uses OAuth tokens
- [x] Foundation Model access via service principal

---

## Configured API Keys

All API keys are configured in `app.yaml` and working:

| API | Env Variable | Status |
|-----|--------------|--------|
| Finnhub (Stocks) | `FINNHUB_API_KEY` | ✅ Working |
| FRED (Economic) | `FRED_API_KEY` | ✅ Working |
| NASA FIRMS (Wildfires) | `NASA_FIRMS_API_KEY` | ✅ Working |
| UCDP (Conflicts) | `UCDP_ACCESS_TOKEN` | ✅ Working |
| Foundation Model | `SERVING_ENDPOINT` | ✅ Working |

**Not Configured:**
| API | Env Variable | Required For |
|-----|--------------|--------------|
| ACLED | `ACLED_EMAIL`, `ACLED_PASSWORD` | Real-time conflict events |

---

## Test Data

### Sample Market Response
```json
{
  "quotes": [
    {"symbol": "SPY", "price": 686.71, "change_percent": 0.94},
    {"symbol": "QQQ", "price": 612.54, "change_percent": 1.82},
    {"symbol": "DIA", "price": 488.38, "change_percent": 0.59},
    {"symbol": "IWM", "price": 262.17, "change_percent": 1.13},
    {"symbol": "VTI", "price": 338.83, "change_percent": 0.92}
  ]
}
```

### Sample Earthquake Response
```json
{
  "earthquakes": [
    {
      "id": "us7000s1pp",
      "magnitude": 5.3,
      "place": "Pagan region, Northern Mariana Islands",
      "latitude": 18.8779,
      "longitude": 145.6537,
      "depth": 191.318,
      "time": "2026-03-04T15:30:00Z",
      "alert": null
    }
  ],
  "total": 168
}
```

### Sample Cyber Threat Response
```json
{
  "threats": [
    {
      "id": "urlhaus-3789152",
      "ioc_type": "url",
      "ioc_value": "http://182.116.123.111:60683/bin.sh",
      "threat_type": "malware_download",
      "malware_family": "Mozi",
      "confidence": 80,
      "source": "URLhaus"
    }
  ],
  "total": 100
}
```

---

## Continuous Integration

### Recommended CI Pipeline

```yaml
# .github/workflows/test.yml
name: Test World Monitor

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run API tests
        run: |
          uv run pytest tests/ -v

      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build

      - name: Lint frontend
        run: |
          cd frontend
          npm run lint
```

---

## Feature Test: Vessel Selection & Route Highlighting

### TC-007: Vessel Route Selection
**Steps:**
1. Navigate to Maritime section
2. Enable Maritime layer (toggle ON)
3. Click "Routes" button to load historical tracks
4. Click on a vessel in the vessel list

**Expected:**
- Selected vessel route glows with highlight effect
- Other vessel routes dim to 25% opacity
- Vessel list shows selection state
- Click again to deselect

**Result:** ✅ Pass (2026-03-03)

### TC-008: Hybrid Data Architecture
**Steps:**
1. Load Maritime section with Routes enabled
2. Observe vessel positions (real-time from Lakebase)
3. Observe vessel routes (historical from Delta Lake)

**Expected:**
- Current positions show sub-10ms latency (Lakebase PostgreSQL)
- Historical routes show 30 days of data (Unity Catalog Delta Lake)
- Both data sources merge seamlessly

**Result:** ✅ Pass - Demonstrates Lakebase + Lakehouse working together

---

## Contact

For issues or questions:
- **App URL**: https://worldmonitor-dev-7474645572615955.aws.databricksapps.com
- **App Logs**: https://worldmonitor-dev-7474645572615955.aws.databricksapps.com/logz
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **API Documentation**: [API.md](API.md)
- **Data Dictionary**: [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
