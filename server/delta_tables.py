"""
Delta Lake table definitions for World Monitor data persistence.
Uses Unity Catalog for governance and Change Data Feed for incremental updates.
"""

import os
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

# Unity Catalog configuration - configurable via environment variables
CATALOG = os.environ.get("CATALOG", "serverless_stable_3n0ihb_catalog")
SCHEMA = os.environ.get("SCHEMA", "worldmonitor_dev")
SCHEMA_CURATED = f"{SCHEMA}_curated"


@dataclass
class TableDefinition:
    """Delta table definition with schema and partitioning."""
    name: str
    columns: list[tuple[str, str]]  # (name, type)
    partition_cols: list[str]
    cluster_cols: Optional[list[str]] = None
    cdf_enabled: bool = True
    comment: str = ""


# ============================================================================
# RAW DATA TABLES - Ingested from external APIs
# ============================================================================

CONFLICT_EVENTS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.conflict_events",
    columns=[
        ("event_id", "STRING"),
        ("event_date", "DATE"),
        ("event_type", "STRING"),
        ("sub_event_type", "STRING"),
        ("country", "STRING"),
        ("admin1", "STRING"),  # Region/State
        ("admin2", "STRING"),  # District
        ("location", "STRING"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("fatalities", "INT"),
        ("actors", "ARRAY<STRING>"),
        ("notes", "STRING"),
        ("source", "STRING"),
        ("source_scale", "STRING"),
        ("timestamp", "TIMESTAMP"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["event_date"],
    cluster_cols=["country", "event_type"],
    comment="ACLED and UCDP conflict events with daily partitioning"
)

EARTHQUAKE_EVENTS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.earthquake_events",
    columns=[
        ("event_id", "STRING"),
        ("time", "TIMESTAMP"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("depth", "DOUBLE"),
        ("magnitude", "DOUBLE"),
        ("magnitude_type", "STRING"),
        ("place", "STRING"),
        ("status", "STRING"),
        ("tsunami", "BOOLEAN"),
        ("felt", "INT"),
        ("cdi", "DOUBLE"),  # Community Decimal Intensity
        ("mmi", "DOUBLE"),  # Modified Mercalli Intensity
        ("alert", "STRING"),
        ("url", "STRING"),
        ("detail_url", "STRING"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["time"],
    cluster_cols=["magnitude", "alert"],
    comment="USGS earthquake data with hourly partitioning"
)

WILDFIRE_EVENTS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.wildfire_events",
    columns=[
        ("fire_id", "STRING"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("brightness", "DOUBLE"),
        ("scan", "DOUBLE"),
        ("track", "DOUBLE"),
        ("acq_date", "DATE"),
        ("acq_time", "STRING"),
        ("satellite", "STRING"),
        ("instrument", "STRING"),
        ("confidence", "INT"),
        ("version", "STRING"),
        ("bright_t31", "DOUBLE"),
        ("frp", "DOUBLE"),  # Fire Radiative Power
        ("daynight", "STRING"),
        ("country", "STRING"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["acq_date"],
    cluster_cols=["country", "confidence"],
    comment="NASA FIRMS active fire detections"
)

MARITIME_VESSELS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.maritime_vessels",
    columns=[
        ("mmsi", "STRING"),
        ("imo", "STRING"),
        ("name", "STRING"),
        ("vessel_type", "STRING"),
        ("flag", "STRING"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("course", "DOUBLE"),
        ("speed", "DOUBLE"),
        ("heading", "INT"),
        ("nav_status", "STRING"),
        ("destination", "STRING"),
        ("eta", "STRING"),
        ("draught", "DOUBLE"),
        ("timestamp", "TIMESTAMP"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["timestamp"],
    cluster_cols=["vessel_type", "flag"],
    comment="AIS vessel tracking positions"
)

MILITARY_AIRCRAFT_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.military_aircraft",
    columns=[
        ("icao24", "STRING"),
        ("callsign", "STRING"),
        ("origin_country", "STRING"),
        ("aircraft_type", "STRING"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("altitude", "DOUBLE"),
        ("velocity", "DOUBLE"),
        ("track", "DOUBLE"),
        ("vertical_rate", "DOUBLE"),
        ("on_ground", "BOOLEAN"),
        ("timestamp", "TIMESTAMP"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["timestamp"],
    cluster_cols=["origin_country", "aircraft_type"],
    comment="ADS-B military aircraft tracks from OpenSky"
)

MARKET_QUOTES_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.market_quotes",
    columns=[
        ("symbol", "STRING"),
        ("asset_type", "STRING"),  # stock, crypto, forex, commodity
        ("name", "STRING"),
        ("price", "DOUBLE"),
        ("change", "DOUBLE"),
        ("change_percent", "DOUBLE"),
        ("volume", "BIGINT"),
        ("market_cap", "DOUBLE"),
        ("high_24h", "DOUBLE"),
        ("low_24h", "DOUBLE"),
        ("currency", "STRING"),
        ("exchange", "STRING"),
        ("timestamp", "TIMESTAMP"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["timestamp"],
    cluster_cols=["asset_type", "symbol"],
    comment="Financial market quotes from Finnhub and CoinGecko"
)

CLIMATE_ANOMALIES_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.climate_anomalies",
    columns=[
        ("location_id", "STRING"),
        ("latitude", "DOUBLE"),
        ("longitude", "DOUBLE"),
        ("location_name", "STRING"),
        ("country", "STRING"),
        ("anomaly_type", "STRING"),  # temperature, precipitation, wind
        ("value", "DOUBLE"),
        ("normal_value", "DOUBLE"),
        ("deviation", "DOUBLE"),
        ("percentile", "INT"),
        ("severity", "STRING"),
        ("date", "DATE"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["date"],
    cluster_cols=["country", "anomaly_type"],
    comment="Open-Meteo climate anomaly data"
)

NEWS_ARTICLES_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.news_articles",
    columns=[
        ("article_id", "STRING"),
        ("title", "STRING"),
        ("link", "STRING"),
        ("source", "STRING"),
        ("category", "STRING"),
        ("published_at", "TIMESTAMP"),
        ("summary", "STRING"),
        ("full_text", "STRING"),
        ("image_url", "STRING"),
        ("tags", "ARRAY<STRING>"),
        ("entities", "ARRAY<STRING>"),  # Named entities extracted
        ("sentiment", "DOUBLE"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["published_at"],
    cluster_cols=["source", "category"],
    comment="RSS news articles with NLP annotations"
)

ECONOMIC_INDICATORS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.economic_indicators",
    columns=[
        ("indicator_id", "STRING"),
        ("source", "STRING"),  # FRED, WorldBank
        ("country_code", "STRING"),
        ("indicator_name", "STRING"),
        ("value", "DOUBLE"),
        ("units", "STRING"),
        ("frequency", "STRING"),
        ("date", "DATE"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["date"],
    cluster_cols=["source", "indicator_id"],
    comment="FRED and World Bank economic indicators"
)

CYBER_THREATS_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.cyber_threats",
    columns=[
        ("ioc_id", "STRING"),
        ("ioc_type", "STRING"),  # url, domain, ip, hash
        ("ioc_value", "STRING"),
        ("threat_type", "STRING"),
        ("malware_family", "STRING"),
        ("confidence", "INT"),
        ("first_seen", "TIMESTAMP"),
        ("last_seen", "TIMESTAMP"),
        ("source", "STRING"),
        ("tags", "ARRAY<STRING>"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["first_seen"],
    cluster_cols=["ioc_type", "threat_type"],
    comment="abuse.ch threat intelligence IOCs"
)

INTERNET_OUTAGES_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA}.internet_outages",
    columns=[
        ("outage_id", "STRING"),
        ("country", "STRING"),
        ("country_code", "STRING"),
        ("asn", "INT"),
        ("asn_name", "STRING"),
        ("start_time", "TIMESTAMP"),
        ("end_time", "TIMESTAMP"),
        ("severity", "STRING"),
        ("source", "STRING"),
        ("ingested_at", "TIMESTAMP"),
    ],
    partition_cols=["start_time"],
    cluster_cols=["country_code", "severity"],
    comment="Cloudflare Radar internet outage annotations"
)


# ============================================================================
# CURATED/AGGREGATED TABLES
# ============================================================================

COUNTRY_RISK_SCORES_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA_CURATED}.country_risk_scores",
    columns=[
        ("country_code", "STRING"),
        ("country_name", "STRING"),
        ("overall_risk", "DOUBLE"),
        ("political_risk", "DOUBLE"),
        ("economic_risk", "DOUBLE"),
        ("security_risk", "DOUBLE"),
        ("climate_risk", "DOUBLE"),
        ("cyber_risk", "DOUBLE"),
        ("calculated_at", "TIMESTAMP"),
    ],
    partition_cols=["calculated_at"],
    cluster_cols=["country_code"],
    comment="Aggregated country risk scores from multiple data sources"
)

CONFLICT_DAILY_SUMMARY_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA_CURATED}.conflict_daily_summary",
    columns=[
        ("date", "DATE"),
        ("country", "STRING"),
        ("event_count", "INT"),
        ("fatalities", "INT"),
        ("by_event_type", "MAP<STRING, INT>"),
        ("by_actor", "MAP<STRING, INT>"),
        ("hotspots", "ARRAY<STRUCT<lat: DOUBLE, lon: DOUBLE, count: INT>>"),
    ],
    partition_cols=["date"],
    cluster_cols=["country"],
    comment="Daily conflict aggregates by country"
)

SEISMIC_WEEKLY_SUMMARY_TABLE = TableDefinition(
    name=f"{CATALOG}.{SCHEMA_CURATED}.seismic_weekly_summary",
    columns=[
        ("week_start", "DATE"),
        ("region", "STRING"),
        ("total_events", "INT"),
        ("max_magnitude", "DOUBLE"),
        ("avg_magnitude", "DOUBLE"),
        ("by_magnitude_range", "MAP<STRING, INT>"),
        ("significant_events", "ARRAY<STRING>"),  # event_ids
    ],
    partition_cols=["week_start"],
    cluster_cols=["region"],
    comment="Weekly seismic activity summary"
)


# ============================================================================
# SQL GENERATION HELPERS
# ============================================================================

def generate_create_table_sql(table: TableDefinition) -> str:
    """Generate CREATE TABLE SQL for a Delta table."""
    columns_sql = ",\n    ".join([f"{col[0]} {col[1]}" for col in table.columns])

    sql = f"""
CREATE TABLE IF NOT EXISTS {table.name} (
    {columns_sql}
)
USING DELTA
"""

    if table.partition_cols:
        sql += f"PARTITIONED BY ({', '.join(table.partition_cols)})\n"

    if table.cluster_cols:
        sql += f"CLUSTER BY ({', '.join(table.cluster_cols)})\n"

    if table.cdf_enabled:
        sql += "TBLPROPERTIES (delta.enableChangeDataFeed = true)\n"

    if table.comment:
        sql += f"COMMENT '{table.comment}'"

    return sql.strip()


def generate_merge_sql(table: TableDefinition, source_table: str, key_cols: list[str]) -> str:
    """Generate MERGE statement for incremental updates."""
    key_conditions = " AND ".join([f"target.{k} = source.{k}" for k in key_cols])
    update_cols = [col[0] for col in table.columns if col[0] not in key_cols]
    update_set = ", ".join([f"target.{c} = source.{c}" for c in update_cols])
    insert_cols = ", ".join([col[0] for col in table.columns])
    insert_vals = ", ".join([f"source.{col[0]}" for col in table.columns])

    return f"""
MERGE INTO {table.name} AS target
USING {source_table} AS source
ON {key_conditions}
WHEN MATCHED THEN UPDATE SET {update_set}
WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
"""


# All table definitions
ALL_TABLES = [
    CONFLICT_EVENTS_TABLE,
    EARTHQUAKE_EVENTS_TABLE,
    WILDFIRE_EVENTS_TABLE,
    MARITIME_VESSELS_TABLE,
    MILITARY_AIRCRAFT_TABLE,
    MARKET_QUOTES_TABLE,
    CLIMATE_ANOMALIES_TABLE,
    NEWS_ARTICLES_TABLE,
    ECONOMIC_INDICATORS_TABLE,
    CYBER_THREATS_TABLE,
    INTERNET_OUTAGES_TABLE,
    COUNTRY_RISK_SCORES_TABLE,
    CONFLICT_DAILY_SUMMARY_TABLE,
    SEISMIC_WEEKLY_SUMMARY_TABLE,
]


if __name__ == "__main__":
    # Print CREATE TABLE statements
    for table in ALL_TABLES:
        print(f"\n-- {table.name}")
        print(generate_create_table_sql(table))
        print(";")
