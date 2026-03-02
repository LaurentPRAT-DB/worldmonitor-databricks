# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Vessel Position History
# MAGIC
# MAGIC This notebook generates 30 days of synthetic vessel position history for the World Monitor demo.
# MAGIC Vessel routes follow major shipping lanes and connect to known port locations.

# COMMAND ----------

# MAGIC %pip install asyncpg
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import math
import random
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, BooleanType, TimestampType

# COMMAND ----------

# Configuration
DAYS_OF_HISTORY = 30
INTERVAL_HOURS = 4  # Position every 4 hours

# COMMAND ----------

# Synthetic vessel data - realistic positions in major shipping lanes
SYNTHETIC_VESSELS = [
    # Mediterranean Sea
    {"mmsi": "244650123", "name": "MAERSK SEALAND", "ship_type": 70, "flag": "NL", "lat": 35.9, "lon": 14.5, "speed": 18.5, "course": 90, "dest": "PIRAEUS"},
    {"mmsi": "636091234", "name": "MSC GENEVA", "ship_type": 70, "flag": "LR", "lat": 36.2, "lon": 5.3, "speed": 16.2, "course": 75, "dest": "BARCELONA"},
    {"mmsi": "538006789", "name": "COSCO SHIPPING", "ship_type": 70, "flag": "MH", "lat": 34.5, "lon": 28.9, "speed": 14.8, "course": 280, "dest": "SUEZ"},
    # English Channel
    {"mmsi": "235089012", "name": "DOVER SPIRIT", "ship_type": 60, "flag": "GB", "lat": 51.0, "lon": 1.4, "speed": 12.5, "course": 220, "dest": "CALAIS"},
    {"mmsi": "227345678", "name": "NORMANDIE EXPRESS", "ship_type": 60, "flag": "FR", "lat": 50.8, "lon": 0.9, "speed": 22.0, "course": 180, "dest": "LE HAVRE"},
    # North Sea
    {"mmsi": "211234567", "name": "HAMBURG BRIDGE", "ship_type": 70, "flag": "DE", "lat": 54.2, "lon": 7.8, "speed": 15.3, "course": 315, "dest": "HAMBURG"},
    {"mmsi": "245678901", "name": "ROTTERDAM EXPRESS", "ship_type": 70, "flag": "NL", "lat": 52.5, "lon": 4.0, "speed": 11.2, "course": 90, "dest": "ROTTERDAM"},
    # Atlantic - US East Coast
    {"mmsi": "367890123", "name": "ATLANTIC STAR", "ship_type": 70, "flag": "US", "lat": 40.5, "lon": -73.8, "speed": 8.5, "course": 270, "dest": "NEW YORK"},
    {"mmsi": "368012345", "name": "CHARLESTON CARRIER", "ship_type": 70, "flag": "US", "lat": 32.8, "lon": -79.9, "speed": 10.2, "course": 180, "dest": "CHARLESTON"},
    {"mmsi": "338123456", "name": "MIAMI TRADER", "ship_type": 70, "flag": "US", "lat": 25.8, "lon": -80.1, "speed": 12.0, "course": 90, "dest": "MIAMI"},
    # Gulf of Mexico
    {"mmsi": "367234567", "name": "GULF PIONEER", "ship_type": 80, "flag": "US", "lat": 29.0, "lon": -89.5, "speed": 6.5, "course": 45, "dest": "NEW ORLEANS"},
    {"mmsi": "345678012", "name": "HOUSTON OIL", "ship_type": 80, "flag": "PA", "lat": 28.5, "lon": -94.2, "speed": 8.0, "course": 350, "dest": "HOUSTON"},
    # Caribbean
    {"mmsi": "352345678", "name": "CARIBBEAN QUEEN", "ship_type": 60, "flag": "PA", "lat": 18.5, "lon": -66.1, "speed": 15.5, "course": 270, "dest": "SAN JUAN"},
    {"mmsi": "309456789", "name": "BAHAMAS EXPRESS", "ship_type": 60, "flag": "BS", "lat": 25.1, "lon": -77.3, "speed": 18.0, "course": 180, "dest": "NASSAU"},
    # Pacific - US West Coast
    {"mmsi": "366789012", "name": "PACIFIC NAVIGATOR", "ship_type": 70, "flag": "US", "lat": 33.7, "lon": -118.3, "speed": 14.5, "course": 270, "dest": "LOS ANGELES"},
    {"mmsi": "369012345", "name": "OAKLAND BRIDGE", "ship_type": 70, "flag": "US", "lat": 37.8, "lon": -122.4, "speed": 10.0, "course": 90, "dest": "OAKLAND"},
    {"mmsi": "367345678", "name": "SEATTLE TRADER", "ship_type": 70, "flag": "US", "lat": 47.6, "lon": -122.4, "speed": 8.5, "course": 180, "dest": "SEATTLE"},
    # Asia - South China Sea
    {"mmsi": "413456789", "name": "SHANGHAI EXPRESS", "ship_type": 70, "flag": "CN", "lat": 22.3, "lon": 114.2, "speed": 16.8, "course": 45, "dest": "HONG KONG"},
    {"mmsi": "416789012", "name": "SHENZHEN STAR", "ship_type": 70, "flag": "CN", "lat": 21.5, "lon": 113.8, "speed": 18.2, "course": 90, "dest": "SHENZHEN"},
    {"mmsi": "533012345", "name": "SINGAPORE SPIRIT", "ship_type": 70, "flag": "SG", "lat": 1.3, "lon": 103.8, "speed": 12.5, "course": 270, "dest": "SINGAPORE"},
    {"mmsi": "548234567", "name": "MANILA BAY", "ship_type": 70, "flag": "PH", "lat": 14.5, "lon": 120.9, "speed": 11.0, "course": 180, "dest": "MANILA"},
    # Japan/Korea
    {"mmsi": "431567890", "name": "TOKYO MARU", "ship_type": 70, "flag": "JP", "lat": 35.4, "lon": 139.8, "speed": 14.0, "course": 90, "dest": "TOKYO"},
    {"mmsi": "440678901", "name": "BUSAN CONTAINER", "ship_type": 70, "flag": "KR", "lat": 35.1, "lon": 129.0, "speed": 15.5, "course": 270, "dest": "BUSAN"},
    # Middle East / Suez
    {"mmsi": "470789012", "name": "DUBAI MERCHANT", "ship_type": 80, "flag": "AE", "lat": 25.3, "lon": 55.3, "speed": 10.5, "course": 180, "dest": "DUBAI"},
    {"mmsi": "622890123", "name": "SUEZ TRANSPORTER", "ship_type": 70, "flag": "EG", "lat": 30.0, "lon": 32.5, "speed": 8.0, "course": 0, "dest": "PORT SAID"},
    {"mmsi": "403901234", "name": "PERSIAN GULF", "ship_type": 80, "flag": "SA", "lat": 26.5, "lon": 50.2, "speed": 12.0, "course": 90, "dest": "DAMMAM"},
    # Indian Ocean
    {"mmsi": "419012345", "name": "MUMBAI CARRIER", "ship_type": 70, "flag": "IN", "lat": 18.9, "lon": 72.8, "speed": 13.5, "course": 270, "dest": "MUMBAI"},
    {"mmsi": "565123456", "name": "COLOMBO TRADER", "ship_type": 70, "flag": "LK", "lat": 6.9, "lon": 79.9, "speed": 11.0, "course": 180, "dest": "COLOMBO"},
    # Africa
    {"mmsi": "601234567", "name": "CAPE TOWN EXPRESS", "ship_type": 70, "flag": "ZA", "lat": -33.9, "lon": 18.4, "speed": 14.0, "course": 90, "dest": "CAPE TOWN"},
    {"mmsi": "627345678", "name": "DURBAN STAR", "ship_type": 70, "flag": "ZA", "lat": -29.9, "lon": 31.0, "speed": 12.5, "course": 180, "dest": "DURBAN"},
    # Australia
    {"mmsi": "503456789", "name": "SYDNEY HARBOUR", "ship_type": 70, "flag": "AU", "lat": -33.8, "lon": 151.2, "speed": 10.0, "course": 90, "dest": "SYDNEY"},
    {"mmsi": "503567890", "name": "MELBOURNE TRADER", "ship_type": 70, "flag": "AU", "lat": -37.8, "lon": 144.9, "speed": 11.5, "course": 270, "dest": "MELBOURNE"},
    # South America
    {"mmsi": "710678901", "name": "SANTOS PIONEER", "ship_type": 70, "flag": "BR", "lat": -23.9, "lon": -46.3, "speed": 13.0, "course": 180, "dest": "SANTOS"},
    {"mmsi": "725789012", "name": "BUENOS AIRES", "ship_type": 70, "flag": "AR", "lat": -34.6, "lon": -58.4, "speed": 9.5, "course": 90, "dest": "BUENOS AIRES"},
    {"mmsi": "730890123", "name": "VALPARAISO STAR", "ship_type": 70, "flag": "CL", "lat": -33.0, "lon": -71.6, "speed": 12.0, "course": 0, "dest": "VALPARAISO"},
    # Panama Canal
    {"mmsi": "352901234", "name": "CANAL NAVIGATOR", "ship_type": 70, "flag": "PA", "lat": 9.0, "lon": -79.5, "speed": 8.0, "course": 315, "dest": "PANAMA"},
    # Tankers in key areas
    {"mmsi": "538112233", "name": "CRUDE CARRIER", "ship_type": 80, "flag": "MH", "lat": 12.5, "lon": 43.5, "speed": 12.0, "course": 180, "dest": "BAB EL MANDEB"},
    {"mmsi": "538223344", "name": "LNG PIONEER", "ship_type": 81, "flag": "MH", "lat": 29.5, "lon": 48.5, "speed": 14.5, "course": 270, "dest": "KUWAIT"},
    {"mmsi": "477334455", "name": "VLCC TITAN", "ship_type": 80, "flag": "HK", "lat": 10.5, "lon": 107.0, "speed": 13.0, "course": 45, "dest": "VUNG TAU"},
]

# COMMAND ----------

# Major shipping waypoints to keep vessels in water
WAYPOINTS = {
    "gibraltar": (36.1, -5.4),
    "sicily_strait": (37.0, 11.5),
    "malta": (35.9, 14.4),
    "crete_south": (34.8, 24.5),
    "suez_north": (31.2, 32.3),
    "dover": (51.1, 1.3),
    "calais": (50.9, 1.8),
    "rotterdam_approach": (52.0, 3.8),
    "hamburg_approach": (54.0, 8.3),
    "new_york_approach": (40.4, -73.5),
    "charleston_approach": (32.6, -79.5),
    "miami_approach": (25.7, -80.0),
    "florida_strait": (24.5, -81.5),
    "gulf_center": (27.0, -90.0),
    "new_orleans_approach": (29.0, -89.2),
    "houston_approach": (29.0, -94.5),
    "puerto_rico_north": (18.8, -66.0),
    "la_approach": (33.5, -118.0),
    "sf_approach": (37.6, -122.5),
    "seattle_approach": (48.0, -124.5),
    "hong_kong": (22.2, 114.1),
    "taiwan_strait": (24.0, 119.5),
    "singapore_strait": (1.2, 103.9),
    "tokyo_bay": (35.3, 139.7),
    "korea_strait": (34.5, 128.5),
    "hormuz": (26.5, 56.5),
    "bab_el_mandeb": (12.6, 43.4),
    "arabian_sea": (15.0, 60.0),
    "mumbai_approach": (18.8, 72.7),
    "colombo_approach": (6.8, 79.8),
    "cape_good_hope": (-34.5, 18.5),
    "sydney_approach": (-33.7, 151.3),
    "melbourne_approach": (-38.0, 144.5),
    "santos_approach": (-24.0, -46.0),
    "buenos_aires_approach": (-35.0, -57.0),
    "valparaiso_approach": (-33.2, -71.8),
    "panama_pacific": (8.9, -79.6),
}

# Route templates: vessel destination -> waypoints to follow
ROUTE_TEMPLATES = {
    "PIRAEUS": ["malta", "sicily_strait", "gibraltar"],
    "BARCELONA": ["sicily_strait", "gibraltar"],
    "SUEZ": ["suez_north", "crete_south", "malta"],
    "CALAIS": ["calais", "dover"],
    "LE HAVRE": ["dover"],
    "HAMBURG": ["hamburg_approach", "rotterdam_approach", "dover"],
    "ROTTERDAM": ["rotterdam_approach", "dover"],
    "NEW YORK": ["new_york_approach"],
    "CHARLESTON": ["charleston_approach", "new_york_approach"],
    "MIAMI": ["miami_approach", "florida_strait"],
    "NEW ORLEANS": ["new_orleans_approach", "gulf_center", "florida_strait"],
    "HOUSTON": ["houston_approach", "gulf_center"],
    "SAN JUAN": ["puerto_rico_north"],
    "NASSAU": ["florida_strait"],
    "LOS ANGELES": ["la_approach"],
    "OAKLAND": ["sf_approach"],
    "SEATTLE": ["seattle_approach", "sf_approach"],
    "HONG KONG": ["hong_kong", "taiwan_strait"],
    "SHENZHEN": ["hong_kong"],
    "SINGAPORE": ["singapore_strait"],
    "MANILA": ["taiwan_strait"],
    "TOKYO": ["tokyo_bay"],
    "BUSAN": ["korea_strait"],
    "DUBAI": ["hormuz", "arabian_sea"],
    "PORT SAID": ["suez_north"],
    "DAMMAM": ["hormuz"],
    "MUMBAI": ["mumbai_approach", "arabian_sea"],
    "COLOMBO": ["colombo_approach"],
    "CAPE TOWN": ["cape_good_hope"],
    "DURBAN": ["cape_good_hope"],
    "SYDNEY": ["sydney_approach"],
    "MELBOURNE": ["melbourne_approach"],
    "SANTOS": ["santos_approach"],
    "BUENOS AIRES": ["buenos_aires_approach"],
    "VALPARAISO": ["valparaiso_approach"],
    "PANAMA": ["panama_pacific"],
    "BAB EL MANDEB": ["bab_el_mandeb"],
    "KUWAIT": ["hormuz"],
    "VUNG TAU": ["singapore_strait"],
}

# COMMAND ----------

def move_point(lat, lon, bearing, distance_nm):
    """Move a point by distance (nautical miles) along a bearing."""
    distance_deg = distance_nm / 60.0
    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)

    new_lat = lat + distance_deg * math.cos(bearing_rad)
    new_lon = lon + distance_deg * math.sin(bearing_rad) / max(math.cos(lat_rad), 0.1)

    # Use floats to ensure DoubleType compatibility
    return max(-85.0, min(85.0, new_lat)), max(-180.0, min(180.0, new_lon))

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points in degrees."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def generate_vessel_route(vessel, days, interval_hours):
    """Generate historical positions for a vessel going backwards in time."""
    positions = []
    current_lat, current_lon = vessel["lat"], vessel["lon"]
    speed_kts = vessel["speed"]
    destination = vessel["dest"]

    # Get waypoints for this route
    waypoints = ROUTE_TEMPLATES.get(destination, [])
    waypoint_coords = [(current_lat, current_lon)]
    for wp_name in waypoints:
        if wp_name in WAYPOINTS:
            waypoint_coords.append(WAYPOINTS[wp_name])

    # Generate positions going backwards in time
    now = datetime.utcnow()
    current_pos = (current_lat, current_lon)
    current_wp_idx = 0

    total_hours = days * 24
    hours_back = 0

    while hours_back < total_hours:
        # Add some speed variation
        actual_speed = max(5, speed_kts + random.uniform(-2, 2))

        # Calculate where vessel was at this time
        time_at_position = now - timedelta(hours=hours_back)

        # Determine bearing to next waypoint
        if current_wp_idx < len(waypoint_coords) - 1:
            next_wp = waypoint_coords[current_wp_idx + 1]
            bearing = calculate_bearing(current_pos[0], current_pos[1], next_wp[0], next_wp[1])
            reverse_bearing = (bearing + 180) % 360
        else:
            reverse_bearing = random.uniform(0, 360)

        # Add course variation
        actual_bearing = (reverse_bearing + random.uniform(-10, 10)) % 360

        # Move backwards along the route
        distance_traveled = actual_speed * interval_hours
        new_lat, new_lon = move_point(current_pos[0], current_pos[1], actual_bearing, distance_traveled)

        positions.append({
            "latitude": new_lat,
            "longitude": new_lon,
            "speed": actual_speed,
            "course": (actual_bearing + 180) % 360,
            "recorded_at": time_at_position,
        })

        current_pos = (new_lat, new_lon)
        hours_back += interval_hours

        # Check if we've reached a waypoint
        if current_wp_idx < len(waypoint_coords) - 1:
            next_wp = waypoint_coords[current_wp_idx + 1]
            dist_to_wp = math.sqrt((current_pos[0] - next_wp[0])**2 + (current_pos[1] - next_wp[1])**2)
            if dist_to_wp < 1:
                current_wp_idx += 1

    # Return in chronological order (oldest first)
    positions.reverse()
    return positions

# COMMAND ----------

# Generate all vessel position data
print(f"Generating {DAYS_OF_HISTORY} days of history for {len(SYNTHETIC_VESSELS)} vessels...")

all_positions = []

for idx, vessel in enumerate(SYNTHETIC_VESSELS):
    synthetic_mmsi = f"999{idx:06d}"

    positions = generate_vessel_route(vessel, DAYS_OF_HISTORY, INTERVAL_HOURS)

    for pos in positions:
        all_positions.append({
            "mmsi": synthetic_mmsi,
            "name": f"{vessel['name']} [DEMO]",
            "ship_type": vessel["ship_type"],
            "flag_country": vessel["flag"],
            "latitude": pos["latitude"],
            "longitude": pos["longitude"],
            "speed": pos["speed"],
            "course": pos["course"],
            "heading": int(pos["course"]),
            "destination": vessel["dest"],
            "is_synthetic": True,
            "recorded_at": pos["recorded_at"],
        })

print(f"Generated {len(all_positions)} total positions")

# COMMAND ----------

# Create DataFrame
schema = StructType([
    StructField("mmsi", StringType(), False),
    StructField("name", StringType(), True),
    StructField("ship_type", IntegerType(), True),
    StructField("flag_country", StringType(), True),
    StructField("latitude", DoubleType(), False),
    StructField("longitude", DoubleType(), False),
    StructField("speed", DoubleType(), True),
    StructField("course", DoubleType(), True),
    StructField("heading", IntegerType(), True),
    StructField("destination", StringType(), True),
    StructField("is_synthetic", BooleanType(), True),
    StructField("recorded_at", TimestampType(), False),
])

df = spark.createDataFrame(all_positions, schema)
display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Lakebase PostgreSQL Database
# MAGIC
# MAGIC Get the Lakebase connection details from the app's environment or secrets.

# COMMAND ----------

# Get database connection from secrets or widgets
try:
    # Try to get from widgets (for manual runs)
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

# If not provided via widgets, try secrets
if not PG_HOST:
    try:
        PG_HOST = dbutils.secrets.get(scope="worldmonitor", key="pg_host")
        PG_DATABASE = dbutils.secrets.get(scope="worldmonitor", key="pg_database")
        PG_USER = dbutils.secrets.get(scope="worldmonitor", key="pg_user")
    except:
        pass

print(f"PG_HOST: {PG_HOST or '(not configured)'}")
print(f"PG_DATABASE: {PG_DATABASE or '(not configured)'}")
print(f"PG_USER: {PG_USER or '(not configured)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option 1: Write directly using JDBC (if Lakebase details are available)

# COMMAND ----------

if PG_HOST and PG_DATABASE and PG_USER:
    # Get OAuth token for Lakebase authentication
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    auth_headers = w.config.authenticate()
    token = auth_headers.get("Authorization", "").replace("Bearer ", "")

    jdbc_url = f"jdbc:postgresql://{PG_HOST}:5432/{PG_DATABASE}?sslmode=require"

    # Write to PostgreSQL
    df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "vessel_positions") \
        .option("user", PG_USER) \
        .option("password", token) \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    print(f"Successfully wrote {df.count()} positions to Lakebase!")
else:
    print("Lakebase not configured. Positions generated but not saved to database.")
    print("To save, configure pg_host, pg_database, pg_user widgets or secrets.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option 2: Save as Delta Table in Unity Catalog (always available)
# MAGIC
# MAGIC Save the data as a Delta table that can be later loaded into Lakebase.

# COMMAND ----------

# Save as Delta table in Unity Catalog
catalog = "serverless_stable_3n0ihb_catalog"
schema = "worldmonitor_dev"

# Create schema if it doesn't exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

# Write to Unity Catalog table
table_name = f"{catalog}.{schema}.vessel_positions_history"
df.write.format("delta").mode("overwrite").saveAsTable(table_name)
print(f"Saved {df.count()} positions to Unity Catalog table: {table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Summary
# MAGIC
# MAGIC Generated vessel position history:
# MAGIC - **Vessels**: 39 synthetic vessels
# MAGIC - **Days of history**: 30 days
# MAGIC - **Interval**: Every 4 hours
# MAGIC - **Total positions**: ~7,000 records
# MAGIC
# MAGIC Routes follow major shipping lanes including:
# MAGIC - Mediterranean Sea
# MAGIC - English Channel / North Sea
# MAGIC - US East Coast (Atlantic)
# MAGIC - Gulf of Mexico
# MAGIC - Caribbean
# MAGIC - US West Coast (Pacific)
# MAGIC - South China Sea
# MAGIC - Japan/Korea
# MAGIC - Middle East / Suez
# MAGIC - Indian Ocean
# MAGIC - Africa (Cape Town, Durban)
# MAGIC - Australia
# MAGIC - South America
# MAGIC - Panama Canal

# COMMAND ----------

# Show sample routes
sample_vessel = "999000000"  # First vessel
sample_df = df.filter(df.mmsi == sample_vessel).orderBy("recorded_at")
print(f"Sample route for {sample_vessel}:")
display(sample_df.select("recorded_at", "latitude", "longitude", "speed", "course").limit(20))
