# World Monitor Testing Documentation

Comprehensive testing guide for the World Monitor Databricks App.

## Test Environment

| Environment | URL | Authentication |
|-------------|-----|----------------|
| **Local Dev** | `http://localhost:8000` | None (demo mode) |
| **Deployed App** | `https://worldmonitor-dev-*.databricksapps.com` | Databricks OAuth |

## API Endpoint Test Results

### Test Date: 2026-03-03

| Category | Endpoint | Status | Notes |
|----------|----------|--------|-------|
| **System** | | | |
| | `GET /api/health` | ✅ Pass | Returns health status |
| | `GET /api/version` | ✅ Pass | Returns version info |
| **Seismology** | | | |
| | `GET /api/seismology/v1/list-earthquakes` | ✅ Pass | USGS data (no API key needed) |
| **Cyber** | | | |
| | `GET /api/cyber/v1/list-cyber-threats` | ✅ Pass | abuse.ch public feeds |
| | `GET /api/cyber/v1/threat-stats` | ✅ Pass | Aggregated statistics |
| **Maritime** | | | |
| | `GET /api/maritime/v1/list-vessels` | ✅ Pass | Synthetic demo data |
| | `GET /api/maritime/v1/vessel-route/{mmsi}` | ✅ Pass | Historical routes from Delta Lake |
| **Intelligence** | | | |
| | `GET /api/intelligence/v1/risk-scores` | ✅ Pass | 14 country risk scores |
| | `GET /api/intelligence/v1/country-brief/{code}` | ✅ Pass | AI-generated briefs |
| | `POST /api/intelligence/v1/ask` | ✅ Pass | Foundation Model chat |
| **Market** | | | |
| | `GET /api/market/v1/quotes` | ⚠️ Requires Key | Needs FINNHUB_API_KEY |
| | `GET /api/market/v1/crypto` | ⚠️ Rate Limited | CoinGecko free tier limits |
| **Wildfire** | | | |
| | `GET /api/wildfire/v1/list-fires` | ❌ Requires Key | Needs NASA_FIRMS_API_KEY |
| **Conflict** | | | |
| | `GET /api/conflict/v1/list-acled-events` | ❌ Requires Key | Needs ACLED credentials |
| | `GET /api/conflict/v1/list-ucdp-events` | ❌ Requires Key | Needs UCDP_ACCESS_TOKEN |
| **Climate** | | | |
| | `GET /api/climate/v1/alerts` | ✅ Pass | Open-Meteo (no key) |
| **News** | | | |
| | `GET /api/news/v1/list-articles` | ✅ Pass | RSS feeds (no key) |
| **Economic** | | | |
| | `GET /api/economic/v1/indicators` | ⚠️ Requires Key | Needs FRED_API_KEY |
| **Military** | | | |
| | `GET /api/military/v1/list-flights` | ⚠️ Rate Limited | OpenSky free tier |
| | `GET /api/military/v1/list-bases` | ✅ Pass | Static data |
| **Infrastructure** | | | |
| | `GET /api/infrastructure/v1/outages` | ✅ Pass | Multi-source aggregation |

### Status Legend
- ✅ **Pass**: Endpoint working correctly
- ⚠️ **Requires Key/Rate Limited**: Works with proper configuration
- ❌ **Requires Key**: Not functional without API key

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

### 1. Missing API Keys
Several data sources require API keys that are not configured:
- **ACLED**: Armed conflict events
- **UCDP**: Conflict fatalities
- **NASA FIRMS**: Satellite fire detection
- **Cloudflare Radar**: Internet outages

**Workaround:** Configure API keys in app.yaml environment variables.

### 2. Rate Limiting
Free tier APIs have rate limits:
- **CoinGecko**: 10-50 calls/minute
- **OpenSky**: Limited without account
- **Finnhub**: 60 calls/minute

**Workaround:** Implement caching (already in place with 15-60 min TTL).

### 3. Synthetic Maritime Data
Real AIS data requires a paid subscription. Current implementation uses synthetic demo vessels.

**Workaround:** Set `USE_SYNTHETIC_MARITIME_DATA=false` when real data source is available.

---

## Deployment Verification Checklist

### Pre-Deployment
- [ ] Frontend build successful (`npm run build`)
- [ ] No TypeScript errors
- [ ] All dependencies in requirements.txt
- [ ] Environment variables configured in app.yaml

### Post-Deployment
- [ ] App accessible at deployed URL
- [ ] Health endpoint returns OK
- [ ] Map loads correctly
- [ ] Data panels show data
- [ ] No console errors
- [ ] AI features work (if Foundation Model configured)

### Security
- [ ] No hardcoded credentials
- [ ] API keys stored in environment variables
- [ ] No sensitive data in logs

---

## Test Data

### Sample Earthquake Response
```json
{
  "earthquakes": [
    {
      "id": "us7000s1pp",
      "magnitude": 5.3,
      "place": "Pagan region, Northern Mariana Islands",
      "location": {
        "latitude": 18.8779,
        "longitude": 145.6537,
        "depth": 191.318
      },
      "occurred_at": 1772548702422,
      "tsunami_warning": false
    }
  ],
  "total": 162
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

## Contact

For issues or questions:
- **App Logs**: `https://worldmonitor-dev-*.databricksapps.com/logz`
- **Documentation**: See docs/ folder
- **Repository**: GitHub
