# World Monitor API Documentation

Complete API reference for World Monitor endpoints.

## Base URL

- **Production**: `https://worldmonitor-dev-XXXX.aws.databricksapps.com`
- **Local Development**: `http://localhost:8000`

## Authentication

Currently, no authentication is required. In production, Databricks Apps handles authentication via the workspace.

---

## System Endpoints

### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "databricks_app": true,
  "demo_mode": false,
  "database": "connected"
}
```

### Version Info

```http
GET /api/version
```

**Response:**
```json
{
  "version": "1.0.0",
  "platform": "databricks-apps",
  "features": {
    "lakebase": true,
    "foundation_models": true
  }
}
```

---

## Conflict API

### List ACLED Events

```http
GET /api/conflict/v1/list-acled-events
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | int | Start timestamp (ms) |
| `end` | int | End timestamp (ms) |
| `country` | string | Country filter |
| `event_types` | string | Pipe-separated types |
| `limit` | int | Max results (default: 1000) |

**Response:**
```json
{
  "events": [
    {
      "id": "acled-12345",
      "event_type": "Battles",
      "country": "Somalia",
      "admin1": "Banadir",
      "location": {
        "latitude": 2.0469,
        "longitude": 45.3182
      },
      "occurred_at": 1709424000000,
      "fatalities": 5,
      "actors": ["Government of Somalia", "Al-Shabaab"],
      "source": "Reuters"
    }
  ],
  "total": 150
}
```

### List UCDP Events

```http
GET /api/conflict/v1/list-ucdp-events
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | int | Start timestamp (ms) |
| `end` | int | End timestamp (ms) |
| `country` | string | Country filter |
| `limit` | int | Max results (default: 1000) |

**Note:** UCDP data covers 2019-2023 (historical).

**Response:**
```json
{
  "events": [
    {
      "id": "ucdp-67890",
      "event_type": "State-based conflict",
      "country": "Afghanistan",
      "admin1": "Kabul",
      "location": {
        "latitude": 34.5553,
        "longitude": 69.2075
      },
      "occurred_at": 1609459200000,
      "fatalities": 12,
      "actors": ["Government of Afghanistan", "Taliban"],
      "source": "UCDP"
    }
  ],
  "total": 500
}
```

### Get Humanitarian Summary

```http
GET /api/conflict/v1/humanitarian-summary/{country_code}
```

**Response:**
```json
{
  "country": "UA",
  "displaced_total": 6500000,
  "refugees": 5400000,
  "idps": 1100000,
  "asylum_seekers": 50000,
  "last_updated": "2026-03-03T12:00:00Z"
}
```

---

## Seismology API

### List Earthquakes

```http
GET /api/seismology/v1/list-earthquakes
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | int | Start timestamp (ms) |
| `end` | int | End timestamp (ms) |
| `min_magnitude` | float | Minimum magnitude |
| `max_magnitude` | float | Maximum magnitude |
| `limit` | int | Max results (default: 500) |

**Response:**
```json
{
  "earthquakes": [
    {
      "id": "us7000n1ab",
      "magnitude": 5.2,
      "magnitude_type": "mb",
      "location": {
        "latitude": 35.6762,
        "longitude": 139.6503
      },
      "depth_km": 45.2,
      "place": "15km NW of Tokyo, Japan",
      "time": 1709510400000,
      "tsunami": false,
      "alert": null,
      "felt_reports": 150,
      "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000n1ab"
    }
  ],
  "total": 162
}
```

---

## Wildfire API

### List Fires

```http
GET /api/wildfire/v1/list-fires
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours_back` | int | Hours to look back (default: 24) |
| `country` | string | Country filter |
| `min_confidence` | string | Confidence: `n`, `l`, `h` |
| `limit` | int | Max results (default: 1000) |

**Response:**
```json
{
  "fires": [
    {
      "id": "firms-20260303-001",
      "location": {
        "latitude": -23.5505,
        "longitude": -46.6333
      },
      "brightness": 312.5,
      "confidence": "h",
      "frp": 45.2,
      "satellite": "MODIS",
      "acq_date": "2026-03-03",
      "acq_time": "14:30",
      "daynight": "D",
      "country": "Brazil"
    }
  ],
  "total": 680
}
```

---

## Maritime API

### List Vessels

```http
GET /api/maritime/v1/list-vessels
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vessel_type` | string | Filter by type |
| `flag` | string | Filter by flag |
| `limit` | int | Max results (default: 100) |

**Response:**
```json
{
  "vessels": [
    {
      "mmsi": "123456789",
      "name": "MAERSK SEALAND",
      "vessel_type": "Cargo",
      "flag": "DK",
      "location": {
        "latitude": 51.9244,
        "longitude": 4.4777
      },
      "course": 245.5,
      "speed": 12.5,
      "destination": "Rotterdam",
      "eta": "2026-03-05T08:00:00Z",
      "timestamp": 1709510400000
    }
  ],
  "total": 50
}
```

### Get Vessel Route

```http
GET /api/maritime/v1/vessel-route/{mmsi}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours_back` | int | Hours of history (default: 24) |

**Response:**
```json
{
  "mmsi": "123456789",
  "name": "MAERSK SEALAND",
  "positions": [
    {
      "latitude": 51.9244,
      "longitude": 4.4777,
      "timestamp": 1709510400000,
      "speed": 12.5,
      "course": 245.5
    }
  ],
  "total_positions": 48
}
```

---

## Market API

### Get Quotes

```http
GET /api/market/v1/quotes
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbols` | string | Comma-separated symbols |

**Response:**
```json
{
  "quotes": [
    {
      "symbol": "SPY",
      "name": "SPDR S&P 500 ETF",
      "price": 512.45,
      "change": -10.02,
      "change_percent": -1.92,
      "volume": 45000000,
      "timestamp": 1709510400000
    }
  ]
}
```

### Get Crypto Prices

```http
GET /api/market/v1/crypto
```

**Response:**
```json
{
  "prices": [
    {
      "symbol": "BTC",
      "name": "Bitcoin",
      "price": 65432.10,
      "change_24h": 2.5,
      "market_cap": 1280000000000,
      "volume_24h": 25000000000
    }
  ]
}
```

---

## Intelligence API

### Get Risk Scores

```http
GET /api/intelligence/v1/risk-scores
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `countries` | string | Comma-separated codes |

**Response:**
```json
{
  "scores": [
    {
      "country_code": "UA",
      "country_name": "Ukraine",
      "overall_risk": 90,
      "political_risk": 85,
      "economic_risk": 90,
      "security_risk": 95,
      "climate_risk": 50,
      "last_updated": "2026-03-03T12:00:00Z"
    }
  ],
  "updated_at": 1709510400000
}
```

### Get Country Brief

```http
GET /api/intelligence/v1/country-brief/{country_code}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `refresh` | bool | Force refresh (default: false) |

**Response:**
```json
{
  "country_code": "UA",
  "country_name": "Ukraine",
  "current_situation": "Ongoing armed conflict with Russia...",
  "key_risks": [
    "Continued military operations in eastern regions",
    "Infrastructure damage affecting power grid",
    "Economic strain from prolonged conflict"
  ],
  "outlook": "High risk persists with no immediate resolution expected.",
  "generated_at": "2026-03-03T12:00:00Z",
  "data_sources": ["ACLED", "UCDP", "World Bank", "News Feeds"]
}
```

### Ask AI

```http
POST /api/intelligence/v1/ask
```

**Request Body:**
```json
{
  "question": "What are the current global hotspots for geopolitical risk?",
  "context": "User is viewing Ukraine risk profile"
}
```

**Response:**
```json
{
  "answer": "# Current Global Geopolitical Hotspots\n\n## Critical Risk Zones\n\n### 1. Eastern Europe\n- **Ukraine-Russia Conflict**: Ongoing military operations...\n\n### 2. Middle East\n- **Israel-Palestine**: Persistent tensions...\n\n### 3. Indo-Pacific\n- **Taiwan Strait**: US-China strategic competition...",
  "sources": ["ACLED", "UCDP", "USGS", "NASA FIRMS", "Finnhub", "World Monitor Analysis"],
  "generated_at": "2026-03-03T15:51:57Z"
}
```

---

## Economic API

### Get FRED Indicators

```http
GET /api/economic/v1/fred-data
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `series_ids` | string | Comma-separated FRED IDs |

### Get World Bank Indicators

```http
GET /api/economic/v1/worldbank-data
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `indicators` | string | Comma-separated indicator codes |
| `countries` | string | Comma-separated country codes |

---

## Infrastructure API

### Get Outages

```http
GET /api/infrastructure/v1/outages
```

**Response:**
```json
{
  "outages": [
    {
      "service": "AWS us-east-1",
      "status": "degraded",
      "impact": "Some API latency",
      "started_at": "2026-03-03T10:00:00Z",
      "source": "AWS Status"
    }
  ]
}
```

---

## Military API

### List Military Flights

```http
GET /api/military/v1/list-military-flights
```

**Description:** Returns synthetic military aircraft positions focused on Persian Gulf / Strait of Hormuz region.

**Response:**
```json
{
  "flights": [
    {
      "icao24": "ae1234",
      "callsign": "NAVY90",
      "origin_country": "United States",
      "position": {
        "latitude": 26.5,
        "longitude": 52.3,
        "altitude": 5500
      },
      "velocity": 250,
      "heading": 180,
      "classification": "military",
      "aircraft_type": "P-8A Poseidon",
      "mission_type": "Maritime Patrol",
      "timestamp": 1709510400000
    }
  ],
  "total": 17
}
```

**Aircraft Types:**
| Country | Aircraft | Mission |
|---------|----------|---------|
| United States | P-8A Poseidon | Maritime Patrol |
| United States | RC-135V/W Rivet Joint | SIGINT/ELINT |
| United States | MQ-9 Reaper | ISR |
| Iran | F-14A Tomcat | Air Defense Patrol |
| Iran | Su-35S Flanker-E | Combat Air Patrol |
| Iran | Shahed-136 | Maritime Surveillance |
| Iran | Bell 212/214 | Naval Support |
| UAE | GlobalEye AEW&C | Airborne Early Warning |
| Saudi Arabia | E-3A Sentry AWACS | Airborne Early Warning |

---

### List Military Bases

```http
GET /api/military/v1/list-military-bases
```

**Description:** Returns regional military bases (US/Coalition and Iranian) in the Persian Gulf area.

**Response:**
```json
{
  "bases": [
    {
      "id": "base-001",
      "name": "Al Udeid Air Base",
      "country": "Qatar",
      "position": {
        "latitude": 25.1173,
        "longitude": 51.315
      },
      "base_type": "air",
      "operator": "US Air Force / Qatar Air Force",
      "status": "heightened"
    }
  ],
  "total": 14
}
```

**Base Locations:**
| Base | Country | Type | Operator |
|------|---------|------|----------|
| Al Udeid Air Base | Qatar | Air | US Air Force / Qatar Air Force |
| Naval Support Activity Bahrain | Bahrain | Naval | US Navy 5th Fleet |
| Al Dhafra Air Base | UAE | Air | US Air Force / UAE Air Force |
| Camp Arifjan | Kuwait | Army | US Army Central |
| Prince Sultan Air Base | Saudi Arabia | Air | US/Royal Saudi Air Force |
| Bandar Abbas Naval Base | Iran | Naval | Islamic Republic of Iran Navy |
| Bushehr Air Base | Iran | Air | IRIAF |
| Chabahar Naval Base | Iran | Naval | IRGC Navy |
| Konarak Naval Base | Iran | Naval | IRGC Navy |
| Jask Forward Operating Base | Iran | Naval | IRGC Navy |
| Isfahan Air Base (8th TFB) | Iran | Air | IRIAF |
| Diego Garcia | BIOT | Joint | US Navy / Royal Navy |
| Camp Lemonnier | Djibouti | Joint | US Africa Command |
| Masirah Air Base | Oman | Air | Royal Air Force of Oman |

---

### Get Theater Posture

```http
GET /api/military/v1/theater-posture/{theater}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `theater` | string | Theater name (e.g., `persian-gulf`) |

**Response:**
```json
{
  "theater": "persian-gulf",
  "alert_level": "elevated",
  "assessment": "Iranian naval and air forces conducting increased patrols. IRGC fast boats observed near commercial shipping lanes. US 5th Fleet has increased maritime patrol sorties.",
  "last_updated": "2026-03-05T10:00:00Z"
}
```

**Note:** Military data is synthetic for demonstration purposes.

---

## Cyber API

### Get Threats

```http
GET /api/cyber/v1/threats
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours_back` | int | Hours to look back |
| `ioc_type` | string | Type: `url`, `domain`, `ip`, `hash` |

**Response:**
```json
{
  "threats": [
    {
      "ioc_type": "url",
      "ioc_value": "http://malicious-example.com/payload",
      "threat_type": "malware",
      "malware_family": "Emotet",
      "confidence": 95,
      "first_seen": "2026-03-03T08:00:00Z",
      "source": "abuse.ch"
    }
  ],
  "total": 250
}
```

---

## Error Responses

All endpoints return errors in a consistent format:

```json
{
  "error": "Error type",
  "detail": "Detailed error message"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Rate Limiting

- **Default**: No rate limiting on Databricks Apps
- **External APIs**: Subject to source API rate limits
- **Caching**: Results cached for 15-60 minutes depending on data type

## Pagination

Most list endpoints support:
- `limit` - Maximum results per request
- `offset` - Skip N results (where applicable)

Large result sets are automatically limited to prevent memory issues.
