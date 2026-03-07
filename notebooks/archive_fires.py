# Databricks notebook source
# MAGIC %md
# MAGIC # Archive Fire Detections: Lakebase -> Unity Catalog
# MAGIC
# MAGIC This notebook archives fire detection data from Lakebase (PostgreSQL) to Unity Catalog (Delta).
# MAGIC
# MAGIC **Hybrid Architecture:**
# MAGIC - Lakebase: Recent data (< 7 days) for fast UI interactions
# MAGIC - Unity Catalog: Historical data for cost-effective analytics storage
# MAGIC
# MAGIC **Schedule:** Run daily to archive old fire data.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import os
from datetime import datetime, timedelta

# Unity Catalog configuration
UC_CATALOG = os.environ.get("UC_CATALOG", "serverless_stable_3n0ihb_catalog")
UC_SCHEMA = os.environ.get("UC_SCHEMA", "worldmonitor_dev")
UC_TABLE = "wildfire_events"
FULL_TABLE_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}"

# Lakebase retention threshold (hours) - data older than this is archived
LAKEBASE_RETENTION_HOURS = int(os.environ.get("FIRE_RETENTION_HOURS", "168"))  # 7 days

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
# MAGIC ## Read Old Fire Detections from Lakebase

# COMMAND ----------

# JDBC URL for Lakebase
jdbc_url = f"jdbc:postgresql://{PGHOST}:{PGPORT}/{PGDATABASE}?sslmode=require"

# Query to get fires older than retention threshold
# Map Lakebase columns to Unity Catalog schema
cutoff_query = f"""
(SELECT
    id AS fire_id,
    latitude,
    longitude,
    brightness,
    NULL::DOUBLE PRECISION AS scan,
    NULL::DOUBLE PRECISION AS track,
    DATE(acq_datetime) AS acq_date,
    TO_CHAR(acq_datetime, 'HH24MI') AS acq_time,
    satellite,
    'MODIS' AS instrument,
    CASE
        WHEN confidence >= 80 THEN 'h'
        WHEN confidence >= 50 THEN 'n'
        ELSE 'l'
    END AS confidence,
    '6.1NRT' AS version,
    NULL::DOUBLE PRECISION AS bright_t31,
    frp,
    CASE
        WHEN EXTRACT(HOUR FROM acq_datetime) BETWEEN 6 AND 18 THEN 'D'
        ELSE 'N'
    END AS daynight,
    country,
    recorded_at AS ingested_at
FROM fire_detections
WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
ORDER BY recorded_at ASC
LIMIT 50000) AS fires_to_archive
"""

print(f"Reading fires older than {LAKEBASE_RETENTION_HOURS} hours from Lakebase...")

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
    print(f"Found {record_count} fires to archive")

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
CLUSTER BY (country)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'NASA FIRMS active fire detections archived from Lakebase'
""")

print(f"Table {FULL_TABLE_NAME} is ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append to Unity Catalog Delta Table

# COMMAND ----------

if record_count > 0:
    print(f"Appending {record_count} fires to {FULL_TABLE_NAME}...")

    try:
        # Use MERGE to avoid duplicates (based on fire_id)
        lakebase_df.createOrReplaceTempView("fires_to_archive")

        spark.sql(f"""
        MERGE INTO {FULL_TABLE_NAME} AS target
        USING fires_to_archive AS source
        ON target.fire_id = source.fire_id
        WHEN NOT MATCHED THEN INSERT *
        """)

        print(f"Successfully archived {record_count} fires to Unity Catalog")
    except Exception as e:
        print(f"Error writing to Unity Catalog: {e}")
        dbutils.notebook.exit(f"ERROR: {e}")
else:
    print("No fires to archive - skipping write")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delete Archived Fires from Lakebase

# COMMAND ----------

if record_count > 0:
    print(f"Deleting archived fires from Lakebase...")

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
        DELETE FROM fire_detections
        WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
        """

        cursor.execute(delete_sql)
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Deleted {deleted_count} fires from Lakebase")

    except Exception as e:
        print(f"Error deleting from Lakebase: {e}")
        print("WARNING: Archival succeeded but cleanup failed.")
else:
    print("No fires archived - skipping delete")

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
print("ARCHIVAL SUMMARY - FIRES")
print("="*60)
for k, v in summary.items():
    print(f"  {k}: {v}")
print("="*60)

# Verify UC table has data
uc_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_TABLE_NAME}").collect()[0]["cnt"]
print(f"\nUnity Catalog table now has {uc_count:,} total fire records")

dbutils.notebook.exit(f"SUCCESS: Archived {record_count} fires")
