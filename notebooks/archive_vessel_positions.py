# Databricks notebook source
# MAGIC %md
# MAGIC # Archive Vessel Positions: Lakebase -> Unity Catalog
# MAGIC
# MAGIC This notebook archives vessel position data from Lakebase (PostgreSQL) to Unity Catalog (Delta).
# MAGIC
# MAGIC **Hybrid Architecture:**
# MAGIC - Lakebase: Recent data (< 24 hours) for fast UI interactions
# MAGIC - Unity Catalog: Historical data (> 24 hours) for cost-effective storage
# MAGIC
# MAGIC **Schedule:** Run daily to keep Lakebase lean and move historical data to Delta.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import os
from datetime import datetime, timedelta

# Unity Catalog configuration
UC_CATALOG = os.environ.get("UC_CATALOG", "serverless_stable_3n0ihb_catalog")
UC_SCHEMA = os.environ.get("UC_SCHEMA", "worldmonitor_dev")
UC_TABLE = "vessel_positions_history"
FULL_TABLE_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}"

# Lakebase retention threshold (hours) - data older than this is archived
LAKEBASE_RETENTION_HOURS = int(os.environ.get("LAKEBASE_RETENTION_HOURS", "24"))

print(f"UC Table: {FULL_TABLE_NAME}")
print(f"Lakebase retention: {LAKEBASE_RETENTION_HOURS} hours")
print(f"Archive cutoff: {datetime.utcnow() - timedelta(hours=LAKEBASE_RETENTION_HOURS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Lakebase

# COMMAND ----------

# Get Lakebase connection info from environment (set by Databricks Apps resource binding)
PGHOST = os.environ.get("PGHOST", "")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE", "")
PGUSER = os.environ.get("PGUSER", "")

if not PGHOST:
    print("WARNING: Lakebase not configured (PGHOST not set)")
    print("This notebook requires Lakebase connection. Set environment variables or run from Databricks Apps context.")
    dbutils.notebook.exit("ERROR: Lakebase not configured")

print(f"Lakebase: {PGHOST}:{PGPORT}/{PGDATABASE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Old Positions from Lakebase

# COMMAND ----------

# Use JDBC to read from Lakebase
# Note: In serverless, we use Databricks SQL connector pattern

from databricks.sdk import WorkspaceClient

# Get OAuth token for Lakebase authentication
w = WorkspaceClient()
token = w.config.authenticate()["Authorization"].replace("Bearer ", "")

# JDBC URL for Lakebase
jdbc_url = f"jdbc:postgresql://{PGHOST}:{PGPORT}/{PGDATABASE}?sslmode=require"

# Query to get positions older than retention threshold
cutoff_query = f"""
(SELECT
    mmsi, name, ship_type, flag_country,
    latitude, longitude, speed, course, heading,
    destination, is_synthetic, recorded_at
FROM vessel_positions
WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
ORDER BY recorded_at ASC
LIMIT 50000) AS positions_to_archive
"""

print(f"Reading positions older than {LAKEBASE_RETENTION_HOURS} hours from Lakebase...")

try:
    # Read from Lakebase using JDBC
    lakebase_df = (spark.read
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", cutoff_query)
        .option("user", PGUSER)
        .option("password", token)
        .option("driver", "org.postgresql.Driver")
        .load())

    position_count = lakebase_df.count()
    print(f"Found {position_count} positions to archive")

    if position_count > 0:
        lakebase_df.show(5, truncate=False)
except Exception as e:
    print(f"Error reading from Lakebase: {e}")
    dbutils.notebook.exit(f"ERROR: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append to Unity Catalog Delta Table

# COMMAND ----------

if position_count > 0:
    print(f"Appending {position_count} positions to {FULL_TABLE_NAME}...")

    try:
        # Append to Delta table
        (lakebase_df.write
            .format("delta")
            .mode("append")
            .saveAsTable(FULL_TABLE_NAME))

        print(f"Successfully archived {position_count} positions to Unity Catalog")
    except Exception as e:
        print(f"Error writing to Unity Catalog: {e}")
        dbutils.notebook.exit(f"ERROR: {e}")
else:
    print("No positions to archive - skipping write")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delete Archived Positions from Lakebase

# COMMAND ----------

if position_count > 0:
    print(f"Deleting archived positions from Lakebase...")

    # Use psycopg2 for direct DELETE (JDBC doesn't support DELETE well)
    import subprocess
    import sys

    # Install psycopg2 if needed
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

        # Delete positions older than retention threshold
        delete_sql = f"""
        DELETE FROM vessel_positions
        WHERE recorded_at < NOW() - INTERVAL '{LAKEBASE_RETENTION_HOURS} hours'
        """

        cursor.execute(delete_sql)
        deleted_count = cursor.rowcount
        conn.commit()

        cursor.close()
        conn.close()

        print(f"Deleted {deleted_count} positions from Lakebase")

    except Exception as e:
        print(f"Error deleting from Lakebase: {e}")
        # Don't exit - archival was successful, just cleanup failed
        print("WARNING: Archival succeeded but cleanup failed. Positions may be duplicated on next run.")
else:
    print("No positions archived - skipping delete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Print summary
summary = {
    "timestamp": datetime.utcnow().isoformat(),
    "lakebase_retention_hours": LAKEBASE_RETENTION_HOURS,
    "positions_archived": position_count,
    "uc_table": FULL_TABLE_NAME,
    "status": "SUCCESS"
}

print("\n" + "="*60)
print("ARCHIVAL SUMMARY")
print("="*60)
for k, v in summary.items():
    print(f"  {k}: {v}")
print("="*60)

# Verify UC table has data
uc_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_TABLE_NAME}").collect()[0]["cnt"]
print(f"\nUnity Catalog table now has {uc_count:,} total positions")

# Check Lakebase remaining
try:
    remaining_df = (spark.read
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", "(SELECT COUNT(*) as cnt FROM vessel_positions) AS remaining")
        .option("user", PGUSER)
        .option("password", token)
        .option("driver", "org.postgresql.Driver")
        .load())

    remaining_count = remaining_df.collect()[0]["cnt"]
    print(f"Lakebase now has {remaining_count:,} positions (recent data)")
except Exception as e:
    print(f"Could not check Lakebase count: {e}")

dbutils.notebook.exit(f"SUCCESS: Archived {position_count} positions")
