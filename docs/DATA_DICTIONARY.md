# Data Dictionary

Complete schema documentation for World Monitor Delta Lake tables.

## Overview

World Monitor uses Unity Catalog for data governance with two schema types:
- **Raw Tables** (`worldmonitor_dev`): Ingested data from external APIs
- **Curated Tables** (`worldmonitor_dev_curated`): Aggregated/processed data

All tables use Delta Lake format with:
- **Change Data Feed** enabled for incremental processing
- **Liquid Clustering** for optimized query performance
- **Time-based partitioning** for efficient data retrieval

---

## Raw Data Tables

### conflict_events

**Description:** ACLED and UCDP armed conflict events with daily partitioning.

**Source:** ACLED API, UCDP API

**Refresh:** Daily

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| event_id | STRING | NOT NULL | Unique event identifier | `acled-12345` |
| event_date | DATE | NOT NULL | Date of the event | `2026-03-03` |
| event_type | STRING | NOT NULL | Type of conflict event | `Battles`, `Violence against civilians` |
| sub_event_type | STRING | YES | Subtype classification | `Armed clash`, `Attack` |
| country | STRING | NOT NULL | Country name | `Somalia` |
| admin1 | STRING | YES | Region/State | `Banadir` |
| admin2 | STRING | YES | District | `Mogadishu` |
| location | STRING | YES | Specific location name | `Central Mogadishu` |
| latitude | DOUBLE | NOT NULL | Latitude coordinate | `2.0469` |
| longitude | DOUBLE | NOT NULL | Longitude coordinate | `45.3182` |
| fatalities | INT | NOT NULL | Number of fatalities | `5` |
| actors | ARRAY<STRING> | YES | Involved parties | `["Government", "Al-Shabaab"]` |
| notes | STRING | YES | Event description | `Armed clash between...` |
| source | STRING | YES | Data source | `ACLED`, `UCDP` |
| source_scale | STRING | YES | Source reliability | `National`, `International` |
| timestamp | TIMESTAMP | NOT NULL | Event timestamp | `2026-03-03T12:00:00Z` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `event_date`
**Clustering:** `country`, `event_type`

---

### earthquake_events

**Description:** USGS earthquake data with hourly partitioning.

**Source:** USGS Earthquake API

**Refresh:** Real-time (every 5 minutes)

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| event_id | STRING | NOT NULL | USGS event ID | `us7000n1ab` |
| time | TIMESTAMP | NOT NULL | Event time (UTC) | `2026-03-03T10:30:00Z` |
| latitude | DOUBLE | NOT NULL | Latitude | `35.6762` |
| longitude | DOUBLE | NOT NULL | Longitude | `139.6503` |
| depth | DOUBLE | NOT NULL | Depth in km | `45.2` |
| magnitude | DOUBLE | NOT NULL | Magnitude value | `5.2` |
| magnitude_type | STRING | YES | Magnitude scale | `mb`, `ml`, `mw` |
| place | STRING | YES | Location description | `15km NW of Tokyo, Japan` |
| status | STRING | YES | Review status | `reviewed`, `automatic` |
| tsunami | BOOLEAN | NOT NULL | Tsunami warning | `false` |
| felt | INT | YES | Number of felt reports | `150` |
| cdi | DOUBLE | YES | Community Decimal Intensity | `4.5` |
| mmi | DOUBLE | YES | Modified Mercalli Intensity | `5.0` |
| alert | STRING | YES | Alert level | `null`, `green`, `yellow`, `red` |
| url | STRING | YES | USGS event page URL | `https://earthquake.usgs.gov/...` |
| detail_url | STRING | YES | GeoJSON detail URL | `https://...` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `time`
**Clustering:** `magnitude`, `alert`

---

### wildfire_events

**Description:** NASA FIRMS active fire detections from satellite.

**Source:** NASA FIRMS API (MODIS, VIIRS)

**Refresh:** Every 6 hours

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| fire_id | STRING | NOT NULL | Unique fire ID | `firms-20260303-001` |
| latitude | DOUBLE | NOT NULL | Latitude | `-23.5505` |
| longitude | DOUBLE | NOT NULL | Longitude | `-46.6333` |
| brightness | DOUBLE | NOT NULL | Brightness temperature (K) | `312.5` |
| scan | DOUBLE | YES | Along scan pixel size | `1.0` |
| track | DOUBLE | YES | Along track pixel size | `1.0` |
| acq_date | DATE | NOT NULL | Acquisition date | `2026-03-03` |
| acq_time | STRING | NOT NULL | Acquisition time (HHMM) | `1430` |
| satellite | STRING | NOT NULL | Satellite source | `Terra`, `Aqua`, `N20` |
| instrument | STRING | NOT NULL | Instrument | `MODIS`, `VIIRS` |
| confidence | STRING | NOT NULL | Detection confidence | `n` (nominal), `l` (low), `h` (high) |
| version | STRING | YES | Algorithm version | `6.1NRT` |
| bright_t31 | DOUBLE | YES | Channel 31 brightness | `298.5` |
| frp | DOUBLE | YES | Fire Radiative Power (MW) | `45.2` |
| daynight | STRING | NOT NULL | Day/Night flag | `D`, `N` |
| country | STRING | YES | Country name | `Brazil` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `acq_date`
**Clustering:** `country`

---

### maritime_vessels

**Description:** AIS vessel tracking positions.

**Source:** AIS Stream / Synthetic Demo Data

**Refresh:** Real-time / Demo: 30-day history

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| mmsi | STRING | NOT NULL | Maritime Mobile Service Identity | `123456789` |
| imo | STRING | YES | IMO ship number | `9876543` |
| name | STRING | YES | Vessel name | `MAERSK SEALAND` |
| vessel_type | STRING | YES | Vessel type | `Cargo`, `Tanker`, `Passenger` |
| flag | STRING | YES | Flag state (ISO 2) | `DK`, `PA`, `LR` |
| latitude | DOUBLE | NOT NULL | Current latitude | `51.9244` |
| longitude | DOUBLE | NOT NULL | Current longitude | `4.4777` |
| course | DOUBLE | YES | Course over ground (degrees) | `245.5` |
| speed | DOUBLE | YES | Speed over ground (knots) | `12.5` |
| heading | INT | YES | Heading (degrees) | `243` |
| nav_status | STRING | YES | Navigation status | `Under way using engine` |
| destination | STRING | YES | Destination port | `Rotterdam` |
| eta | STRING | YES | Estimated time of arrival | `2026-03-05T08:00` |
| draught | DOUBLE | YES | Current draught (m) | `10.5` |
| timestamp | TIMESTAMP | NOT NULL | Position timestamp | `2026-03-03T15:00:00Z` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `timestamp`
**Clustering:** `vessel_type`, `flag`

---

### military_aircraft

**Description:** ADS-B military aircraft tracks from OpenSky Network.

**Source:** OpenSky Network API

**Refresh:** Every 5 minutes

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| icao24 | STRING | NOT NULL | ICAO 24-bit address | `ae1234` |
| callsign | STRING | YES | Flight callsign | `REACH123` |
| origin_country | STRING | NOT NULL | Country of origin | `United States` |
| aircraft_type | STRING | YES | Aircraft type | `C-17`, `F-16`, `E-3` |
| latitude | DOUBLE | NOT NULL | Latitude | `38.8977` |
| longitude | DOUBLE | NOT NULL | Longitude | `-77.0365` |
| altitude | DOUBLE | YES | Barometric altitude (m) | `10668` |
| velocity | DOUBLE | YES | Ground speed (m/s) | `250` |
| track | DOUBLE | YES | Track angle (degrees) | `180` |
| vertical_rate | DOUBLE | YES | Vertical rate (m/s) | `0` |
| on_ground | BOOLEAN | NOT NULL | On ground flag | `false` |
| timestamp | TIMESTAMP | NOT NULL | Position timestamp | `2026-03-03T15:00:00Z` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `timestamp`
**Clustering:** `origin_country`, `aircraft_type`

---

### market_quotes

**Description:** Financial market quotes from Finnhub and CoinGecko.

**Source:** Finnhub API, CoinGecko API

**Refresh:** Real-time (1 minute)

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| symbol | STRING | NOT NULL | Trading symbol | `SPY`, `BTC` |
| asset_type | STRING | NOT NULL | Asset type | `stock`, `crypto`, `forex` |
| name | STRING | YES | Full name | `SPDR S&P 500 ETF Trust` |
| price | DOUBLE | NOT NULL | Current price | `512.45` |
| change | DOUBLE | YES | Price change | `-10.02` |
| change_percent | DOUBLE | YES | Percent change | `-1.92` |
| volume | BIGINT | YES | Trading volume | `45000000` |
| market_cap | DOUBLE | YES | Market capitalization | `1280000000000` |
| high_24h | DOUBLE | YES | 24-hour high | `525.00` |
| low_24h | DOUBLE | YES | 24-hour low | `510.00` |
| currency | STRING | YES | Quote currency | `USD` |
| exchange | STRING | YES | Exchange name | `NASDAQ`, `NYSE` |
| timestamp | TIMESTAMP | NOT NULL | Quote timestamp | `2026-03-03T15:00:00Z` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `timestamp`
**Clustering:** `asset_type`, `symbol`

---

### news_articles

**Description:** RSS news articles with NLP annotations.

**Source:** RSS feeds (Reuters, AP, BBC, Al Jazeera)

**Refresh:** Every 15 minutes

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| article_id | STRING | NOT NULL | Article hash ID | `news-abc123` |
| title | STRING | NOT NULL | Article title | `Ukraine Updates: Latest...` |
| link | STRING | NOT NULL | Article URL | `https://reuters.com/...` |
| source | STRING | NOT NULL | News source | `Reuters` |
| category | STRING | YES | Topic category | `World`, `Business`, `Politics` |
| published_at | TIMESTAMP | NOT NULL | Publication time | `2026-03-03T14:00:00Z` |
| summary | STRING | YES | Article summary | `Summary text...` |
| full_text | STRING | YES | Full article text | `Full article...` |
| image_url | STRING | YES | Featured image URL | `https://...` |
| tags | ARRAY<STRING> | YES | Topic tags | `["Ukraine", "Russia"]` |
| entities | ARRAY<STRING> | YES | Named entities | `["Kyiv", "Zelenskyy"]` |
| sentiment | DOUBLE | YES | Sentiment score (-1 to 1) | `-0.35` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `published_at`
**Clustering:** `source`, `category`

---

### economic_indicators

**Description:** FRED and World Bank economic indicators.

**Source:** FRED API, World Bank API

**Refresh:** Daily

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| indicator_id | STRING | NOT NULL | Indicator code | `GDP`, `UNRATE` |
| source | STRING | NOT NULL | Data source | `FRED`, `WorldBank` |
| country_code | STRING | YES | ISO country code | `US`, `DE` |
| indicator_name | STRING | NOT NULL | Full indicator name | `Gross Domestic Product` |
| value | DOUBLE | NOT NULL | Indicator value | `25462.7` |
| units | STRING | YES | Unit of measure | `Billions of Dollars` |
| frequency | STRING | YES | Data frequency | `Quarterly`, `Annual` |
| date | DATE | NOT NULL | Observation date | `2026-01-01` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `date`
**Clustering:** `source`, `indicator_id`

---

### cyber_threats

**Description:** abuse.ch threat intelligence IOCs.

**Source:** abuse.ch APIs (URLhaus, MalwareBazaar)

**Refresh:** Hourly

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| ioc_id | STRING | NOT NULL | IOC identifier | `urlhaus-123456` |
| ioc_type | STRING | NOT NULL | IOC type | `url`, `domain`, `ip`, `hash` |
| ioc_value | STRING | NOT NULL | IOC value | `http://malicious.com/payload` |
| threat_type | STRING | YES | Threat classification | `malware`, `phishing` |
| malware_family | STRING | YES | Malware family | `Emotet`, `QakBot` |
| confidence | INT | YES | Confidence score (0-100) | `95` |
| first_seen | TIMESTAMP | NOT NULL | First seen timestamp | `2026-03-03T08:00:00Z` |
| last_seen | TIMESTAMP | YES | Last seen timestamp | `2026-03-03T14:00:00Z` |
| source | STRING | NOT NULL | Source feed | `URLhaus`, `MalwareBazaar` |
| tags | ARRAY<STRING> | YES | Tags | `["trojan", "banking"]` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `first_seen`
**Clustering:** `ioc_type`, `threat_type`

---

### internet_outages

**Description:** Cloudflare Radar internet outage annotations.

**Source:** Cloudflare Radar API

**Refresh:** Every 15 minutes

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| outage_id | STRING | NOT NULL | Outage identifier | `outage-12345` |
| country | STRING | NOT NULL | Country name | `Iran` |
| country_code | STRING | NOT NULL | ISO country code | `IR` |
| asn | INT | YES | Autonomous System Number | `12345` |
| asn_name | STRING | YES | ASN organization | `Example ISP` |
| start_time | TIMESTAMP | NOT NULL | Outage start time | `2026-03-03T10:00:00Z` |
| end_time | TIMESTAMP | YES | Outage end time | `2026-03-03T14:00:00Z` |
| severity | STRING | NOT NULL | Severity level | `partial`, `complete` |
| source | STRING | NOT NULL | Data source | `Cloudflare Radar` |
| ingested_at | TIMESTAMP | NOT NULL | Ingestion timestamp | `2026-03-03T15:00:00Z` |

**Partitioning:** `start_time`
**Clustering:** `country_code`, `severity`

---

## Curated Tables

### country_risk_scores

**Description:** Aggregated country risk scores from multiple data sources.

**Source:** Calculated from conflict, economic, climate, and cyber data

**Refresh:** Daily

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| country_code | STRING | NOT NULL | ISO 2-letter code | `UA` |
| country_name | STRING | NOT NULL | Country name | `Ukraine` |
| overall_risk | DOUBLE | NOT NULL | Overall risk score (0-100) | `90` |
| political_risk | DOUBLE | NOT NULL | Political risk component | `85` |
| economic_risk | DOUBLE | NOT NULL | Economic risk component | `90` |
| security_risk | DOUBLE | NOT NULL | Security risk component | `95` |
| climate_risk | DOUBLE | NOT NULL | Climate risk component | `50` |
| cyber_risk | DOUBLE | YES | Cyber risk component | `60` |
| calculated_at | TIMESTAMP | NOT NULL | Calculation timestamp | `2026-03-03T00:00:00Z` |

**Partitioning:** `calculated_at`
**Clustering:** `country_code`

---

### conflict_daily_summary

**Description:** Daily conflict aggregates by country.

**Source:** Aggregated from `conflict_events`

**Refresh:** Daily

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| date | DATE | NOT NULL | Summary date | `2026-03-03` |
| country | STRING | NOT NULL | Country name | `Somalia` |
| event_count | INT | NOT NULL | Number of events | `15` |
| fatalities | INT | NOT NULL | Total fatalities | `42` |
| by_event_type | MAP<STRING, INT> | YES | Events by type | `{"Battles": 8, "Violence": 7}` |
| by_actor | MAP<STRING, INT> | YES | Events by actor | `{"Al-Shabaab": 10}` |
| hotspots | ARRAY<STRUCT> | YES | Geographic hotspots | `[{lat, lon, count}]` |

**Partitioning:** `date`
**Clustering:** `country`

---

## Data Quality Rules

### Validation Rules

| Table | Rule | Description |
|-------|------|-------------|
| All | `latitude BETWEEN -90 AND 90` | Valid latitude range |
| All | `longitude BETWEEN -180 AND 180` | Valid longitude range |
| earthquake_events | `magnitude >= 0` | Non-negative magnitude |
| conflict_events | `fatalities >= 0` | Non-negative fatalities |
| market_quotes | `price > 0` | Positive prices |
| cyber_threats | `confidence BETWEEN 0 AND 100` | Valid confidence range |

### Freshness SLAs

| Table | Max Staleness | Alert Threshold |
|-------|---------------|-----------------|
| earthquake_events | 10 minutes | 15 minutes |
| market_quotes | 5 minutes | 10 minutes |
| wildfire_events | 12 hours | 24 hours |
| conflict_events | 48 hours | 72 hours |
| news_articles | 30 minutes | 1 hour |

---

## Data Retention

| Table Type | Retention Period | Archive Policy |
|------------|------------------|----------------|
| Raw Tables | 90 days | Archive to cold storage |
| Curated Tables | 1 year | Aggregate older data |
| Cache Tables | 24 hours | Auto-purge |

---

## Access Patterns

### Common Queries

**Recent earthquakes by magnitude:**
```sql
SELECT * FROM earthquake_events
WHERE time >= current_timestamp() - INTERVAL 24 HOURS
  AND magnitude >= 4.0
ORDER BY magnitude DESC
```

**Conflict hotspots:**
```sql
SELECT country, COUNT(*) as events, SUM(fatalities) as total_fatalities
FROM conflict_events
WHERE event_date >= current_date() - INTERVAL 30 DAYS
GROUP BY country
ORDER BY events DESC
LIMIT 10
```

**Active fires by country:**
```sql
SELECT country, COUNT(*) as fire_count, AVG(frp) as avg_intensity
FROM wildfire_events
WHERE acq_date = current_date()
  AND confidence = 'h'
GROUP BY country
ORDER BY fire_count DESC
```
