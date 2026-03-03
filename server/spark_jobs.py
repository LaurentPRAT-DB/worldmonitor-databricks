"""
Spark Structured Streaming jobs for data ingestion.
Run these as Databricks Jobs on a scheduled basis.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, current_timestamp, from_json, explode,
    to_timestamp, to_date, struct, array, when, concat
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    IntegerType, LongType, BooleanType, ArrayType, TimestampType
)
from datetime import datetime, timedelta
import os
import requests

# Import table definitions - handle both package and standalone execution
try:
    from .delta_tables import (
        CONFLICT_EVENTS_TABLE,
        EARTHQUAKE_EVENTS_TABLE,
        WILDFIRE_EVENTS_TABLE,
        MARKET_QUOTES_TABLE,
        CLIMATE_ANOMALIES_TABLE,
        NEWS_ARTICLES_TABLE,
        ECONOMIC_INDICATORS_TABLE,
        CYBER_THREATS_TABLE,
    )
except ImportError:
    # Running as standalone script - define table names directly
    # Using Unity Catalog: catalog.schema.table format
    CATALOG = os.environ.get("CATALOG", "serverless_stable_3n0ihb_catalog")
    SCHEMA = os.environ.get("SCHEMA", "worldmonitor_dev")
    print(f"Using catalog={CATALOG}, schema={SCHEMA}")

    class TableDef:
        def __init__(self, name): self.name = name

    CONFLICT_EVENTS_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.conflict_events")
    EARTHQUAKE_EVENTS_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.earthquake_events")
    WILDFIRE_EVENTS_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.wildfire_events")
    MARKET_QUOTES_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.market_quotes")
    CLIMATE_ANOMALIES_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.climate_anomalies")
    NEWS_ARTICLES_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.news_articles")
    ECONOMIC_INDICATORS_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.economic_indicators")
    CYBER_THREATS_TABLE = TableDef(f"{CATALOG}.{SCHEMA}.cyber_threats")


def get_spark() -> SparkSession:
    """Get or create Spark session."""
    return SparkSession.builder.getOrCreate()


# ============================================================================
# ACLED CONFLICT DATA INGESTION
# ============================================================================

def ingest_acled_conflicts(api_key: str, days_back: int = 7):
    """Ingest ACLED conflict events into Delta table."""
    spark = get_spark()

    # Fetch from ACLED API
    base_url = "https://api.acleddata.com/acled/read"
    params = {
        "key": api_key,
        "terms": "accept",
        "event_date": (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
        "event_date_where": ">=",
        "limit": 10000,
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"ACLED API error: {response.status_code}")
        return

    data = response.json().get("data", [])
    if not data:
        print("No ACLED data to ingest")
        return

    # Convert to DataFrame
    df = spark.createDataFrame(data)

    # Transform to target schema
    transformed = df.select(
        col("data_id").alias("event_id"),
        to_date(col("event_date")).alias("event_date"),
        col("event_type"),
        col("sub_event_type"),
        col("country"),
        col("admin1"),
        col("admin2"),
        col("location"),
        col("latitude").cast(DoubleType()),
        col("longitude").cast(DoubleType()),
        col("fatalities").cast(IntegerType()),
        array(col("actor1"), col("actor2")).alias("actors"),
        col("notes"),
        col("source"),
        col("source_scale"),
        to_timestamp(col("timestamp")).alias("timestamp"),
        current_timestamp().alias("ingested_at"),
    )

    # Merge into Delta table
    transformed.createOrReplaceTempView("acled_staging")

    spark.sql(f"""
        MERGE INTO {CONFLICT_EVENTS_TABLE.name} AS target
        USING acled_staging AS source
        ON target.event_id = source.event_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    print(f"Ingested {transformed.count()} ACLED conflict events")


# ============================================================================
# USGS EARTHQUAKE DATA INGESTION
# ============================================================================

def ingest_usgs_earthquakes(min_magnitude: float = 2.5, days_back: int = 7):
    """Ingest USGS earthquake events into Delta table."""
    spark = get_spark()

    # Fetch from USGS API
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_back)

    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": start_time.isoformat(),
        "endtime": end_time.isoformat(),
        "minmagnitude": min_magnitude,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"USGS API error: {response.status_code}")
        return

    features = response.json().get("features", [])
    if not features:
        print("No USGS earthquake data to ingest")
        return

    # Flatten GeoJSON features with explicit type casting
    records = []
    for f in features:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])
        records.append({
            "event_id": f.get("id"),
            "time": datetime.fromtimestamp(props.get("time", 0) / 1000),
            "latitude": float(coords[1]) if coords[1] is not None else 0.0,
            "longitude": float(coords[0]) if coords[0] is not None else 0.0,
            "depth": float(coords[2]) if coords[2] is not None else 0.0,
            "magnitude": float(props.get("mag")) if props.get("mag") is not None else None,
            "magnitude_type": props.get("magType"),
            "place": props.get("place"),
            "status": props.get("status"),
            "tsunami": bool(props.get("tsunami")),
            "felt": int(props.get("felt")) if props.get("felt") is not None else None,
            "cdi": float(props.get("cdi")) if props.get("cdi") is not None else None,
            "mmi": float(props.get("mmi")) if props.get("mmi") is not None else None,
            "alert": props.get("alert"),
            "url": props.get("url"),
            "detail_url": props.get("detail"),
        })

    # Define explicit schema to avoid type inference issues
    from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType, BooleanType, IntegerType
    schema = StructType([
        StructField("event_id", StringType(), True),
        StructField("time", TimestampType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("depth", DoubleType(), True),
        StructField("magnitude", DoubleType(), True),
        StructField("magnitude_type", StringType(), True),
        StructField("place", StringType(), True),
        StructField("status", StringType(), True),
        StructField("tsunami", BooleanType(), True),
        StructField("felt", IntegerType(), True),
        StructField("cdi", DoubleType(), True),
        StructField("mmi", DoubleType(), True),
        StructField("alert", StringType(), True),
        StructField("url", StringType(), True),
        StructField("detail_url", StringType(), True),
    ])
    df = spark.createDataFrame(records, schema=schema)
    df = df.withColumn("ingested_at", current_timestamp())

    # Merge into Delta table
    df.createOrReplaceTempView("usgs_staging")

    spark.sql(f"""
        MERGE INTO {EARTHQUAKE_EVENTS_TABLE.name} AS target
        USING usgs_staging AS source
        ON target.event_id = source.event_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    print(f"Ingested {len(records)} USGS earthquake events")


# ============================================================================
# NASA FIRMS WILDFIRE DATA INGESTION
# ============================================================================

def ingest_nasa_fires(map_key: str, days_back: int = 1):
    """Ingest NASA FIRMS active fire data into Delta table."""
    spark = get_spark()

    # Fetch from FIRMS API
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{map_key}/VIIRS_SNPP_NRT/world/{days_back}"

    response = requests.get(url)
    if response.status_code != 200:
        print(f"FIRMS API error: {response.status_code}")
        return

    # Parse CSV response
    import io
    import pandas as pd

    csv_data = io.StringIO(response.text)
    pdf = pd.read_csv(csv_data)

    if pdf.empty:
        print("No FIRMS fire data to ingest")
        return

    # Convert to Spark DataFrame
    df = spark.createDataFrame(pdf)

    # Transform to target schema
    transformed = df.select(
        concat(col("latitude").cast(StringType()), lit("_"),
               col("longitude").cast(StringType()), lit("_"),
               col("acq_date")).alias("fire_id"),
        col("latitude").cast(DoubleType()),
        col("longitude").cast(DoubleType()),
        col("bright_ti4").alias("brightness").cast(DoubleType()),
        col("scan").cast(DoubleType()),
        col("track").cast(DoubleType()),
        to_date(col("acq_date")).alias("acq_date"),
        col("acq_time").cast(StringType()),
        col("satellite"),
        col("instrument"),
        col("confidence").cast(IntegerType()),
        col("version"),
        col("bright_ti5").alias("bright_t31").cast(DoubleType()),
        col("frp").cast(DoubleType()),
        col("daynight"),
        lit("").alias("country"),
        current_timestamp().alias("ingested_at"),
    )

    # Append to Delta table (fires are point-in-time, no merge needed)
    transformed.write.format("delta").mode("append").saveAsTable(WILDFIRE_EVENTS_TABLE.name)

    print(f"Ingested {transformed.count()} FIRMS fire detections")


# ============================================================================
# MARKET DATA INGESTION
# ============================================================================

def ingest_market_quotes(finnhub_key: str, symbols: list[str] = None):
    """Ingest market quotes from Finnhub into Delta table."""
    spark = get_spark()

    if symbols is None:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "SPY"]

    records = []
    for symbol in symbols:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("c"):  # Current price exists
                records.append({
                    "symbol": symbol,
                    "asset_type": "stock",
                    "name": symbol,
                    "price": data.get("c"),
                    "change": data.get("d"),
                    "change_percent": data.get("dp"),
                    "volume": data.get("v"),
                    "market_cap": None,
                    "high_24h": data.get("h"),
                    "low_24h": data.get("l"),
                    "currency": "USD",
                    "exchange": "US",
                    "timestamp": datetime.utcnow(),
                })

    if records:
        df = spark.createDataFrame(records)
        df = df.withColumn("ingested_at", current_timestamp())
        df.write.format("delta").mode("append").saveAsTable(MARKET_QUOTES_TABLE.name)
        print(f"Ingested {len(records)} market quotes")


# ============================================================================
# NEWS ARTICLES INGESTION
# ============================================================================

def ingest_rss_news(feeds: dict[str, str]):
    """Ingest RSS news articles into Delta table."""
    import feedparser

    spark = get_spark()
    records = []

    for source, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:50]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6])
                else:
                    pub_dt = datetime.utcnow()

                records.append({
                    "article_id": entry.get("id", entry.get("link", "")),
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "source": source,
                    "category": "news",
                    "published_at": pub_dt,
                    "summary": entry.get("summary", "")[:500],
                    "full_text": None,
                    "image_url": None,
                    "tags": [],
                    "entities": [],
                    "sentiment": None,
                })
        except Exception as e:
            print(f"Error parsing {source}: {e}")

    if records:
        # Define explicit schema to avoid type inference issues with None/empty values
        from pyspark.sql.types import StructType, StructField, StringType, TimestampType, ArrayType, DoubleType
        schema = StructType([
            StructField("article_id", StringType(), True),
            StructField("title", StringType(), True),
            StructField("link", StringType(), True),
            StructField("source", StringType(), True),
            StructField("category", StringType(), True),
            StructField("published_at", TimestampType(), True),
            StructField("summary", StringType(), True),
            StructField("full_text", StringType(), True),
            StructField("image_url", StringType(), True),
            StructField("tags", ArrayType(StringType()), True),
            StructField("entities", ArrayType(StringType()), True),
            StructField("sentiment", DoubleType(), True),
        ])
        df = spark.createDataFrame(records, schema=schema)
        df = df.withColumn("ingested_at", current_timestamp())

        # Merge to deduplicate
        df.createOrReplaceTempView("news_staging")
        spark.sql(f"""
            MERGE INTO {NEWS_ARTICLES_TABLE.name} AS target
            USING news_staging AS source
            ON target.article_id = source.article_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        print(f"Ingested {len(records)} news articles")


# ============================================================================
# CYBER THREAT INTEL INGESTION
# ============================================================================

def ingest_cyber_threats(days_back: int = 7):
    """Ingest cyber threat IOCs from abuse.ch into Delta table."""
    spark = get_spark()
    records = []

    # ThreatFox API
    url = "https://threatfox-api.abuse.ch/api/v1/"
    response = requests.post(url, json={"query": "get_iocs", "days": days_back})

    if response.status_code == 200:
        data = response.json()
        for item in data.get("data", [])[:1000]:
            ioc_type = item.get("ioc_type", "").lower()
            if "ip" in ioc_type:
                mapped_type = "ip"
            elif "domain" in ioc_type:
                mapped_type = "domain"
            elif "url" in ioc_type:
                mapped_type = "url"
            elif "hash" in ioc_type or "md5" in ioc_type or "sha" in ioc_type:
                mapped_type = "hash"
            else:
                mapped_type = "other"

            try:
                first_seen = datetime.strptime(
                    item.get("first_seen", "1970-01-01 00:00:00 UTC"),
                    "%Y-%m-%d %H:%M:%S UTC"
                )
            except Exception:
                first_seen = datetime.utcnow()

            records.append({
                "ioc_id": str(item.get("id", "")),
                "ioc_type": mapped_type,
                "ioc_value": item.get("ioc", ""),
                "threat_type": item.get("threat_type", "unknown"),
                "malware_family": item.get("malware_printable"),
                "confidence": int(item.get("confidence_level", 50)),
                "first_seen": first_seen,
                "last_seen": datetime.utcnow(),
                "source": "ThreatFox",
                "tags": item.get("tags", []) or [],
            })

    if records:
        # Define explicit schema to avoid type inference issues
        from pyspark.sql.types import StructType, StructField, StringType, TimestampType, ArrayType, IntegerType
        schema = StructType([
            StructField("ioc_id", StringType(), True),
            StructField("ioc_type", StringType(), True),
            StructField("ioc_value", StringType(), True),
            StructField("threat_type", StringType(), True),
            StructField("malware_family", StringType(), True),
            StructField("confidence", IntegerType(), True),
            StructField("first_seen", TimestampType(), True),
            StructField("last_seen", TimestampType(), True),
            StructField("source", StringType(), True),
            StructField("tags", ArrayType(StringType()), True),
        ])
        df = spark.createDataFrame(records, schema=schema)
        df = df.withColumn("ingested_at", current_timestamp())

        df.createOrReplaceTempView("cyber_staging")
        spark.sql(f"""
            MERGE INTO {CYBER_THREATS_TABLE.name} AS target
            USING cyber_staging AS source
            ON target.ioc_id = source.ioc_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """)

        print(f"Ingested {len(records)} cyber threat IOCs")


# ============================================================================
# ECONOMIC INDICATORS INGESTION
# ============================================================================

def ingest_fred_indicators(api_key: str, series_ids: list[str] = None):
    """Ingest FRED economic indicators into Delta table."""
    spark = get_spark()

    if series_ids is None:
        series_ids = [
            "DGS10",     # 10-Year Treasury
            "FEDFUNDS",  # Fed Funds Rate
            "UNRATE",    # Unemployment Rate
            "CPIAUCSL",  # CPI
            "GDPC1",     # Real GDP
        ]

    records = []
    for series_id in series_ids:
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "limit": 10,
            "sort_order": "desc",
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for obs in data.get("observations", []):
                try:
                    value = float(obs.get("value", 0))
                    records.append({
                        "indicator_id": series_id,
                        "source": "FRED",
                        "country_code": "US",
                        "indicator_name": series_id,
                        "value": value,
                        "units": "",
                        "frequency": "",
                        "date": datetime.strptime(obs.get("date"), "%Y-%m-%d").date(),
                    })
                except (ValueError, TypeError):
                    continue

    if records:
        df = spark.createDataFrame(records)
        df = df.withColumn("ingested_at", current_timestamp())

        df.createOrReplaceTempView("fred_staging")
        spark.sql(f"""
            MERGE INTO {ECONOMIC_INDICATORS_TABLE.name} AS target
            USING fred_staging AS source
            ON target.indicator_id = source.indicator_id AND target.date = source.date
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """)

        print(f"Ingested {len(records)} FRED indicators")


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def run_all_ingestion_jobs(config: dict):
    """Run all data ingestion jobs."""
    print(f"Starting data ingestion at {datetime.utcnow()}")

    if config.get("acled_key"):
        ingest_acled_conflicts(config["acled_key"])

    ingest_usgs_earthquakes()

    if config.get("firms_key"):
        ingest_nasa_fires(config["firms_key"])

    if config.get("finnhub_key"):
        ingest_market_quotes(config["finnhub_key"])

    ingest_rss_news({
        "Reuters": "https://feeds.reuters.com/reuters/worldNews",
        "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    })

    ingest_cyber_threats()

    if config.get("fred_key"):
        ingest_fred_indicators(config["fred_key"])

    print(f"Data ingestion completed at {datetime.utcnow()}")


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="World Monitor Data Ingestion Jobs")
    parser.add_argument("--job", type=str, required=True,
                        choices=["conflicts", "earthquakes", "fires", "market", "news", "cyber", "economic", "all"],
                        help="Which ingestion job to run")
    args = parser.parse_args()

    # Get API keys from environment (set via Databricks job secrets)
    config = {
        "acled_key": os.environ.get("ACLED_API_KEY"),
        "firms_key": os.environ.get("NASA_FIRMS_KEY"),
        "finnhub_key": os.environ.get("FINNHUB_API_KEY"),
        "fred_key": os.environ.get("FRED_API_KEY"),
    }

    print(f"Running job: {args.job}")

    if args.job == "all":
        run_all_ingestion_jobs(config)
    elif args.job == "conflicts":
        if config["acled_key"]:
            ingest_acled_conflicts(config["acled_key"])
        else:
            print("ACLED_API_KEY not set, skipping conflicts ingestion")
    elif args.job == "earthquakes":
        ingest_usgs_earthquakes()
    elif args.job == "fires":
        if config["firms_key"]:
            ingest_nasa_fires(config["firms_key"])
        else:
            print("NASA_FIRMS_KEY not set, skipping fire ingestion")
    elif args.job == "market":
        if config["finnhub_key"]:
            ingest_market_quotes(config["finnhub_key"])
        else:
            print("FINNHUB_API_KEY not set, skipping market ingestion")
    elif args.job == "news":
        ingest_rss_news({
            "Reuters": "https://feeds.reuters.com/reuters/worldNews",
            "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
        })
    elif args.job == "cyber":
        ingest_cyber_threats()
    elif args.job == "economic":
        if config["fred_key"]:
            ingest_fred_indicators(config["fred_key"])
        else:
            print("FRED_API_KEY not set, skipping economic ingestion")

    print(f"Job {args.job} completed")
