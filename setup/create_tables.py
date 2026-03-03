"""
Setup script to create Unity Catalog resources for World Monitor.
Run this as a Databricks notebook or job to initialize the data infrastructure.

Usage:
  - Set CATALOG and SCHEMA environment variables, or use defaults
  - Run via Databricks job or notebook
"""

import os
from pyspark.sql import SparkSession


def get_spark() -> SparkSession:
    """Get or create Spark session."""
    return SparkSession.builder.getOrCreate()


def create_catalog_and_schemas(spark: SparkSession, catalog: str, schema: str):
    """Create schemas if they don't exist (uses existing catalog)."""

    # Use existing catalog - don't try to create it
    print(f"Using catalog: {catalog}")
    spark.sql(f"USE CATALOG {catalog}")

    print(f"Creating schema: {catalog}.{schema}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    curated_schema = f"{schema}_curated"
    print(f"Creating schema: {catalog}.{curated_schema}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{curated_schema}")

    print("Schemas created successfully")


def create_raw_tables(spark: SparkSession, catalog: str, schema: str):
    """Create the raw data tables."""

    tables = [
        # Conflict Events
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.conflict_events (
            event_id STRING,
            event_date DATE,
            event_type STRING,
            sub_event_type STRING,
            country STRING,
            admin1 STRING,
            admin2 STRING,
            location STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            fatalities INT,
            actors ARRAY<STRING>,
            notes STRING,
            source STRING,
            source_scale STRING,
            timestamp TIMESTAMP,
            ingested_at TIMESTAMP
        )
        USING DELTA
        PARTITIONED BY (event_date)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'ACLED and UCDP conflict events with daily partitioning'
        """,

        # Earthquake Events
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.earthquake_events (
            event_id STRING,
            time TIMESTAMP,
            latitude DOUBLE,
            longitude DOUBLE,
            depth DOUBLE,
            magnitude DOUBLE,
            magnitude_type STRING,
            place STRING,
            status STRING,
            tsunami BOOLEAN,
            felt INT,
            cdi DOUBLE,
            mmi DOUBLE,
            alert STRING,
            url STRING,
            detail_url STRING,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'USGS earthquake data'
        """,

        # Wildfire Events
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.wildfire_events (
            fire_id STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            brightness DOUBLE,
            scan DOUBLE,
            track DOUBLE,
            acq_date DATE,
            acq_time STRING,
            satellite STRING,
            instrument STRING,
            confidence STRING,
            version STRING,
            bright_t31 DOUBLE,
            frp DOUBLE,
            daynight STRING,
            country STRING,
            ingested_at TIMESTAMP
        )
        USING DELTA
        PARTITIONED BY (acq_date)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'NASA FIRMS active fire detections - confidence is n/l/h (nominal/low/high)'
        """,

        # Maritime Vessels
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.maritime_vessels (
            mmsi STRING,
            imo STRING,
            name STRING,
            vessel_type STRING,
            flag STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            course DOUBLE,
            speed DOUBLE,
            heading INT,
            nav_status STRING,
            destination STRING,
            eta STRING,
            draught DOUBLE,
            timestamp TIMESTAMP,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'AIS vessel tracking positions'
        """,

        # Military Aircraft
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.military_aircraft (
            icao24 STRING,
            callsign STRING,
            origin_country STRING,
            aircraft_type STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            altitude DOUBLE,
            velocity DOUBLE,
            track DOUBLE,
            vertical_rate DOUBLE,
            on_ground BOOLEAN,
            timestamp TIMESTAMP,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'ADS-B military aircraft tracks from OpenSky'
        """,

        # Market Quotes
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.market_quotes (
            symbol STRING,
            asset_type STRING,
            name STRING,
            price DOUBLE,
            change DOUBLE,
            change_percent DOUBLE,
            volume BIGINT,
            market_cap DOUBLE,
            high_24h DOUBLE,
            low_24h DOUBLE,
            currency STRING,
            exchange STRING,
            timestamp TIMESTAMP,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Financial market quotes from Finnhub and CoinGecko'
        """,

        # Climate Anomalies
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.climate_anomalies (
            location_id STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            location_name STRING,
            country STRING,
            anomaly_type STRING,
            value DOUBLE,
            normal_value DOUBLE,
            deviation DOUBLE,
            percentile INT,
            severity STRING,
            date DATE,
            ingested_at TIMESTAMP
        )
        USING DELTA
        PARTITIONED BY (date)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Open-Meteo climate anomaly data'
        """,

        # News Articles
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.news_articles (
            article_id STRING,
            title STRING,
            link STRING,
            source STRING,
            category STRING,
            published_at TIMESTAMP,
            summary STRING,
            full_text STRING,
            image_url STRING,
            tags ARRAY<STRING>,
            entities ARRAY<STRING>,
            sentiment DOUBLE,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'RSS news articles with NLP annotations'
        """,

        # Economic Indicators
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.economic_indicators (
            indicator_id STRING,
            source STRING,
            country_code STRING,
            indicator_name STRING,
            value DOUBLE,
            units STRING,
            frequency STRING,
            date DATE,
            ingested_at TIMESTAMP
        )
        USING DELTA
        PARTITIONED BY (date)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'FRED and World Bank economic indicators'
        """,

        # Cyber Threats
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.cyber_threats (
            ioc_id STRING,
            ioc_type STRING,
            ioc_value STRING,
            threat_type STRING,
            malware_family STRING,
            confidence INT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            source STRING,
            tags ARRAY<STRING>,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'abuse.ch threat intelligence IOCs'
        """,

        # Internet Outages
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.internet_outages (
            outage_id STRING,
            country STRING,
            country_code STRING,
            asn INT,
            asn_name STRING,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            severity STRING,
            source STRING,
            ingested_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Cloudflare Radar internet outage annotations'
        """,
    ]

    for ddl in tables:
        table_name = ddl.split("CREATE TABLE IF NOT EXISTS ")[1].split(" ")[0]
        print(f"Creating table: {table_name}")
        spark.sql(ddl)

    print(f"Created {len(tables)} raw tables")


def create_curated_tables(spark: SparkSession, catalog: str, schema: str):
    """Create the curated/aggregated tables."""

    curated_schema = f"{schema}_curated"

    tables = [
        # Country Risk Scores
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{curated_schema}.country_risk_scores (
            country_code STRING,
            country_name STRING,
            overall_risk DOUBLE,
            political_risk DOUBLE,
            economic_risk DOUBLE,
            security_risk DOUBLE,
            climate_risk DOUBLE,
            cyber_risk DOUBLE,
            calculated_at TIMESTAMP
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Aggregated country risk scores from multiple data sources'
        """,

        # Conflict Daily Summary
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{curated_schema}.conflict_daily_summary (
            date DATE,
            country STRING,
            event_count INT,
            fatalities INT,
            by_event_type MAP<STRING, INT>,
            by_actor MAP<STRING, INT>
        )
        USING DELTA
        PARTITIONED BY (date)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Daily conflict aggregates by country'
        """,

        # Seismic Weekly Summary
        f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{curated_schema}.seismic_weekly_summary (
            week_start DATE,
            region STRING,
            total_events INT,
            max_magnitude DOUBLE,
            avg_magnitude DOUBLE,
            by_magnitude_range MAP<STRING, INT>,
            significant_events ARRAY<STRING>
        )
        USING DELTA
        PARTITIONED BY (week_start)
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Weekly seismic activity summary'
        """,
    ]

    for ddl in tables:
        table_name = ddl.split("CREATE TABLE IF NOT EXISTS ")[1].split(" ")[0]
        print(f"Creating table: {table_name}")
        spark.sql(ddl)

    print(f"Created {len(tables)} curated tables")


def main():
    """Main entry point for table creation."""
    # Get configuration from environment - use workspace catalog by default
    catalog = os.environ.get("CATALOG", "serverless_stable_3n0ihb_catalog")
    schema = os.environ.get("SCHEMA", "worldmonitor_dev")

    print(f"=" * 60)
    print(f"World Monitor - Unity Catalog Setup")
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    print(f"=" * 60)

    spark = get_spark()

    # Create catalog and schemas
    create_catalog_and_schemas(spark, catalog, schema)

    # Create raw data tables
    create_raw_tables(spark, catalog, schema)

    # Create curated tables
    create_curated_tables(spark, catalog, schema)

    print(f"=" * 60)
    print("Setup complete!")
    print(f"=" * 60)


if __name__ == "__main__":
    main()
