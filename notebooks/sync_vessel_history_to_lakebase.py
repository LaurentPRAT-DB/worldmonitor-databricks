# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Vessel History from Unity Catalog to Lakebase
# MAGIC
# MAGIC This notebook syncs vessel position history from the Unity Catalog Delta table
# MAGIC to Lakebase PostgreSQL for the World Monitor app API.

# COMMAND ----------

# MAGIC %pip install asyncpg
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession

# COMMAND ----------

# Configuration
UC_CATALOG = "serverless_stable_3n0ihb_catalog"
UC_SCHEMA = "worldmonitor_dev"
UC_TABLE = "vessel_positions_history"

# Lakebase connection - get from app resources or secrets
try:
    dbutils.widgets.text("pg_host", "", "PostgreSQL Host")
    dbutils.widgets.text("pg_database", "", "Database Name")
    dbutils.widgets.text("pg_user", "", "Database User")

    PG_HOST = dbutils.widgets.get("pg_host")
    PG_DATABASE = dbutils.widgets.get("pg_database")
    PG_USER = dbutils.widgets.get("pg_user")
except:
    PG_HOST = ""
    PG_DATABASE = ""
    PG_USER = ""

# Fallback to secrets if widgets not provided
if not PG_HOST:
    try:
        PG_HOST = dbutils.secrets.get(scope="worldmonitor", key="pg_host")
        PG_DATABASE = dbutils.secrets.get(scope="worldmonitor", key="pg_database")
        PG_USER = dbutils.secrets.get(scope="worldmonitor", key="pg_user")
    except:
        pass

print(f"Unity Catalog: {UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}")
print(f"Lakebase Host: {PG_HOST or '(not configured)'}")
print(f"Lakebase Database: {PG_DATABASE or '(not configured)'}")

# COMMAND ----------

# Read from Unity Catalog
source_table = f"{UC_CATALOG}.{UC_SCHEMA}.{UC_TABLE}"
df = spark.read.table(source_table)

record_count = df.count()
print(f"Read {record_count} records from {source_table}")

# Show sample
display(df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Lakebase

# COMMAND ----------

if PG_HOST and PG_DATABASE and PG_USER:
    # Get OAuth token for Lakebase authentication
    w = WorkspaceClient()
    auth_headers = w.config.authenticate()
    token = auth_headers.get("Authorization", "").replace("Bearer ", "")

    jdbc_url = f"jdbc:postgresql://{PG_HOST}:5432/{PG_DATABASE}?sslmode=require"

    print(f"Writing {record_count} records to Lakebase...")

    # Write to vessel_positions table (used by API)
    df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "vessel_positions") \
        .option("user", PG_USER) \
        .option("password", token) \
        .option("driver", "org.postgresql.Driver") \
        .mode("overwrite") \
        .save()

    print(f"Successfully synced {record_count} positions to Lakebase!")
else:
    print("ERROR: Lakebase not configured.")
    print("Please provide pg_host, pg_database, pg_user via widgets or secrets.")
    dbutils.notebook.exit("FAILED: Lakebase credentials not configured")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Sync

# COMMAND ----------

if PG_HOST and PG_DATABASE and PG_USER:
    # Read back from Lakebase to verify
    verify_df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "vessel_positions") \
        .option("user", PG_USER) \
        .option("password", token) \
        .option("driver", "org.postgresql.Driver") \
        .load()

    lakebase_count = verify_df.count()
    print(f"Verification: {lakebase_count} records in Lakebase vessel_positions table")

    if lakebase_count == record_count:
        print("✅ Sync verified successfully!")
    else:
        print(f"⚠️ Count mismatch: UC has {record_count}, Lakebase has {lakebase_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC This notebook syncs vessel position history from Unity Catalog to Lakebase:
# MAGIC - **Source**: `serverless_stable_3n0ihb_catalog.worldmonitor_dev.vessel_positions_history`
# MAGIC - **Target**: Lakebase `vessel_positions` table
# MAGIC - **Mode**: Full overwrite (for historical demo data)
# MAGIC
# MAGIC For incremental sync of real-time data, modify to use merge/upsert logic.
