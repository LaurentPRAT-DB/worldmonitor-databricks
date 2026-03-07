# Databricks notebook source
# MAGIC %md
# MAGIC # Archive Market Quotes: Lakebase -> Unity Catalog
# MAGIC
# MAGIC This notebook archives market quote data from Lakebase (PostgreSQL) to Unity Catalog (Delta).
# MAGIC
# MAGIC **Hybrid Architecture:**
# MAGIC - Lakebase: Recent data (< 24 hours) for fast UI interactions
# MAGIC - Unity Catalog: Historical data for cost-effective analytics storage
# MAGIC
# MAGIC **Schedule:** Run hourly to archive old market quotes.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import os
from datetime import datetime, timedelta

# Unity Catalog configuration
UC_CATALOG = os.environ.get("UC_CATALOG", "serverless_stable_3n0ihb_catalog")
UC_SCHEMA = os.environ.get("UC_SCHEMA", "worldmonitor_dev")
UC_TABLE = "market_quotes"
FULL_TABLE_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}"

# Lakebase retention threshold (hours) - data older than this is archived
LAKEBASE_RETENTION_HOURS = int(os.environ.get("MARKET_RETENTION_HOURS", "24"))  # 24 hours

print(f"UC Table: {FULL_TABLE_NAME}")
print(f"Lakebase retention: {LAKEBASE_RETENTION_HOURS} hours")
print(f"Archive cutoff: {datetime.utcnow() - timedelta(hours=LAKEBASE_RETENTION_HOURS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Lakebase

# COMMAND ----------

from databricks.sdk import WorkspaceClient

# Lakebase Autoscaling configuration
LAKEBASE_ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", "projects/worldmonitor-cache/branches/production/endpoints/primary")
PGHOST = os.environ.get("PGHOST", "ep-winter-dawn-d2ev1vuh.database.us-east-1.cloud.databricks.com")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")

if not PGHOST:
    print("WARNING: Lakebase not configured (PGHOST not set)")
    dbutils.notebook.exit("ERROR: Lakebase not configured")

print(f"Lakebase: {PGHOST}:{PGPORT}/{PGDATABASE}")

# Get OAuth token for Lakebase Autoscaling
w = WorkspaceClient()
cred = w.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT)
token = cred.token

# Get user identity for PGUSER
PGUSER = w.current_user.me().user_name
print(f"Authenticated as: {PGUSER}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Old Market Quotes from Lakebase

# COMMAND ----------

# JDBC URL for Lakebase
jdbc_url = f"jdbc:postgresql://{PGHOST}:{PGPORT}/{PGDATABASE}?sslmode=require"

# Query to get market quotes older than retention threshold
# Map Lakebase columns to Unity Catalog schema
cutoff_query = f"""
(SELECT
    symbol,
    asset_type,
    name,
    price,
    change_value AS change,
    change_percent,
    volume,
    market_cap,
    high_24h,
    low_24h,
    currency,
    exchange,
    recorded_at AS timestamp,
    recorded_at AS ingested_at
FROM market_quotes_history
WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
ORDER BY recorded_at ASC
LIMIT 100000) AS quotes_to_archive
"""

print(f"Reading market quotes older than {LAKEBASE_RETENTION_HOURS} hours from Lakebase...")

try:
    lakebase_df = (spark.read
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", cutoff_query)
        .option("user", PGUSER)
        .option("password", token)
        .option("driver", "org.postgresql.Driver")
        .load())

    record_count = lakebase_df.count()
    print(f"Found {record_count} market quotes to archive")

    if record_count > 0:
        lakebase_df.show(5, truncate=False)
except Exception as e:
    print(f"Error reading from Lakebase: {e}")
    dbutils.notebook.exit(f"ERROR: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ensure Unity Catalog Table Exists

# COMMAND ----------

# Create table if it doesn't exist
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {FULL_TABLE_NAME} (
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
PARTITIONED BY (timestamp)
CLUSTER BY (asset_type, symbol)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'Financial market quotes from Finnhub and CoinGecko archived from Lakebase'
""")

print(f"Table {FULL_TABLE_NAME} is ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append to Unity Catalog Delta Table

# COMMAND ----------

if record_count > 0:
    print(f"Appending {record_count} market quotes to {FULL_TABLE_NAME}...")

    try:
        # For market quotes, just append (no dedup needed as each timestamp is unique)
        (lakebase_df.write
            .format("delta")
            .mode("append")
            .saveAsTable(FULL_TABLE_NAME))

        print(f"Successfully archived {record_count} market quotes to Unity Catalog")
    except Exception as e:
        print(f"Error writing to Unity Catalog: {e}")
        dbutils.notebook.exit(f"ERROR: {e}")
else:
    print("No market quotes to archive - skipping write")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delete Archived Quotes from Lakebase

# COMMAND ----------

if record_count > 0:
    print(f"Deleting archived market quotes from Lakebase...")

    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])

    import psycopg2

    try:
        conn = psycopg2.connect(
            host=PGHOST,
            port=PGPORT,
            database=PGDATABASE,
            user=PGUSER,
            password=token,
            sslmode="require"
        )

        cursor = conn.cursor()
        delete_sql = f"""
        DELETE FROM market_quotes_history
        WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
        """

        cursor.execute(delete_sql)
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Deleted {deleted_count} market quotes from Lakebase")

    except Exception as e:
        print(f"Error deleting from Lakebase: {e}")
        print("WARNING: Archival succeeded but cleanup failed.")
else:
    print("No market quotes archived - skipping delete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

summary = {
    "timestamp": datetime.utcnow().isoformat(),
    "lakebase_retention_hours": LAKEBASE_RETENTION_HOURS,
    "records_archived": record_count,
    "uc_table": FULL_TABLE_NAME,
    "status": "SUCCESS"
}

print("\n" + "="*60)
print("ARCHIVAL SUMMARY - MARKET QUOTES")
print("="*60)
for k, v in summary.items():
    print(f"  {k}: {v}")
print("="*60)

# Verify UC table has data
uc_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_TABLE_NAME}").collect()[0]["cnt"]
print(f"\nUnity Catalog table now has {uc_count:,} total market quote records")

dbutils.notebook.exit(f"SUCCESS: Archived {record_count} market quotes")
