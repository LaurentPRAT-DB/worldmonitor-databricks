# Databricks notebook source
# MAGIC %md
# MAGIC # Archive Earthquakes: Lakebase -> Unity Catalog
# MAGIC
# MAGIC This notebook archives earthquake data from Lakebase (PostgreSQL) to Unity Catalog (Delta).
# MAGIC
# MAGIC **Hybrid Architecture:**
# MAGIC - Lakebase: Recent data (< 30 days) for fast UI interactions
# MAGIC - Unity Catalog: Historical data for cost-effective analytics storage
# MAGIC
# MAGIC **Schedule:** Run weekly to archive old earthquake data.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import os
from datetime import datetime, timedelta

# Unity Catalog configuration
UC_CATALOG = os.environ.get("UC_CATALOG", "serverless_stable_3n0ihb_catalog")
UC_SCHEMA = os.environ.get("UC_SCHEMA", "worldmonitor_dev")
UC_TABLE = "earthquake_events"
FULL_TABLE_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}"

# Lakebase retention threshold (hours) - data older than this is archived
LAKEBASE_RETENTION_HOURS = int(os.environ.get("EARTHQUAKE_RETENTION_HOURS", "720"))  # 30 days

print(f"UC Table: {FULL_TABLE_NAME}")
print(f"Lakebase retention: {LAKEBASE_RETENTION_HOURS} hours ({LAKEBASE_RETENTION_HOURS/24:.0f} days)")
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
# MAGIC ## Read Old Earthquakes from Lakebase

# COMMAND ----------

# JDBC URL for Lakebase
jdbc_url = f"jdbc:postgresql://{PGHOST}:{PGPORT}/{PGDATABASE}?sslmode=require"

# Query to get earthquakes older than retention threshold
# Map Lakebase columns to Unity Catalog schema
cutoff_query = f"""
(SELECT
    id AS event_id,
    TO_TIMESTAMP(occurred_at / 1000) AS time,
    latitude,
    longitude,
    depth,
    magnitude,
    magnitude_type,
    place,
    'reviewed' AS status,
    COALESCE(tsunami, false) AS tsunami,
    0 AS felt,
    NULL::DOUBLE PRECISION AS cdi,
    NULL::DOUBLE PRECISION AS mmi,
    alert,
    url,
    detail_url,
    recorded_at AS ingested_at
FROM earthquakes
WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
ORDER BY recorded_at ASC
LIMIT 50000) AS earthquakes_to_archive
"""

print(f"Reading earthquakes older than {LAKEBASE_RETENTION_HOURS} hours from Lakebase...")

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
    print(f"Found {record_count} earthquakes to archive")

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
PARTITIONED BY (time)
CLUSTER BY (magnitude, alert)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'USGS earthquake data archived from Lakebase'
""")

print(f"Table {FULL_TABLE_NAME} is ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append to Unity Catalog Delta Table

# COMMAND ----------

if record_count > 0:
    print(f"Appending {record_count} earthquakes to {FULL_TABLE_NAME}...")

    try:
        # Use MERGE to avoid duplicates (based on event_id)
        lakebase_df.createOrReplaceTempView("earthquakes_to_archive")

        spark.sql(f"""
        MERGE INTO {FULL_TABLE_NAME} AS target
        USING earthquakes_to_archive AS source
        ON target.event_id = source.event_id
        WHEN NOT MATCHED THEN INSERT *
        """)

        print(f"Successfully archived {record_count} earthquakes to Unity Catalog")
    except Exception as e:
        print(f"Error writing to Unity Catalog: {e}")
        dbutils.notebook.exit(f"ERROR: {e}")
else:
    print("No earthquakes to archive - skipping write")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delete Archived Earthquakes from Lakebase

# COMMAND ----------

if record_count > 0:
    print(f"Deleting archived earthquakes from Lakebase...")

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
        DELETE FROM earthquakes
        WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
        """

        cursor.execute(delete_sql)
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Deleted {deleted_count} earthquakes from Lakebase")

    except Exception as e:
        print(f"Error deleting from Lakebase: {e}")
        print("WARNING: Archival succeeded but cleanup failed.")
else:
    print("No earthquakes archived - skipping delete")

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
print("ARCHIVAL SUMMARY - EARTHQUAKES")
print("="*60)
for k, v in summary.items():
    print(f"  {k}: {v}")
print("="*60)

# Verify UC table has data
uc_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_TABLE_NAME}").collect()[0]["cnt"]
print(f"\nUnity Catalog table now has {uc_count:,} total earthquake records")

dbutils.notebook.exit(f"SUCCESS: Archived {record_count} earthquakes")
