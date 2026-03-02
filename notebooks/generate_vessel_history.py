# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Vessel Position History
# MAGIC
# MAGIC This notebook generates 30 days of synthetic vessel position history for the World Monitor demo.
# MAGIC Vessel routes follow major shipping lanes with dense waypoints to stay in the ocean.

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

# MAGIC %md
# MAGIC ## Ocean Shipping Lanes
# MAGIC
# MAGIC Define dense waypoint sequences that follow actual shipping lanes, staying safely in the ocean.

# COMMAND ----------

# Major shipping lane waypoint sequences (lat, lon)
# These are ordered sequences that vessels follow to stay in the ocean

SHIPPING_LANES = {
    # ===========================================
    # TRANS-ATLANTIC ROUTES (stay in ocean!)
    # ===========================================

    # North Atlantic - Europe to US East Coast (great circle route)
    "atlantic_north_eu_us": [
        (50.0, -5.0),    # Western approaches UK
        (51.0, -10.0),   # Off Ireland
        (52.0, -15.0),   # Eastern Atlantic
        (52.5, -20.0),   # Mid-North Atlantic
        (52.0, -25.0),   # North Atlantic
        (51.0, -30.0),   # Central Atlantic
        (49.0, -35.0),   # Western Atlantic
        (46.0, -40.0),   # Grand Banks approach
        (44.0, -50.0),   # Off Newfoundland
        (42.0, -60.0),   # Nova Scotia offshore
        (41.0, -66.0),   # Georges Bank
        (40.5, -70.0),   # Nantucket offshore
        (40.0, -73.0),   # New York approach
    ],

    # North Atlantic - reverse direction with slightly different path
    "atlantic_north_us_eu": [
        (40.5, -73.5),   # New York
        (41.5, -68.0),   # Off Cape Cod
        (43.0, -60.0),   # Off Nova Scotia
        (45.0, -50.0),   # Grand Banks
        (48.0, -40.0),   # Mid Atlantic
        (50.0, -30.0),   # Eastern Atlantic
        (51.0, -20.0),   # Approaching Europe
        (50.0, -10.0),   # Off Ireland
        (49.0, -5.0),    # English Channel approach
    ],

    # South Atlantic - Europe/Med to South America
    "atlantic_south_eu_brazil": [
        (36.0, -5.5),    # Gibraltar
        (33.0, -10.0),   # Off Morocco
        (28.0, -15.0),   # Off Canaries
        (22.0, -18.0),   # Off Mauritania
        (15.0, -20.0),   # Off Senegal
        (10.0, -22.0),   # Off Guinea
        (5.0, -25.0),    # Equatorial Atlantic
        (0.0, -28.0),    # Equator
        (-5.0, -32.0),   # Off Brazil North
        (-10.0, -35.0),  # Off Recife
        (-18.0, -38.0),  # Off Salvador
        (-23.0, -43.0),  # Rio approach
        (-24.0, -46.0),  # Santos
    ],

    # Africa West Coast route (Cape Verde to Cape Town)
    "africa_west_coast": [
        (15.0, -18.0),   # Off Dakar
        (10.0, -16.0),   # Off Guinea-Bissau
        (5.0, -10.0),    # Off Liberia
        (0.0, -5.0),     # Gulf of Guinea West
        (-3.0, 5.0),     # Off Gabon
        (-6.0, 10.0),    # Off Angola
        (-12.0, 12.0),   # Off Angola South
        (-18.0, 11.0),   # Off Namibia
        (-25.0, 13.0),   # Off Namibia South
        (-32.0, 16.0),   # Off South Africa West
        (-34.0, 18.0),   # Cape Town approach
    ],

    # ===========================================
    # TRANS-PACIFIC ROUTES
    # ===========================================

    # Pacific - Asia to North America (great circle)
    "pacific_asia_us_north": [
        (35.0, 140.0),   # Off Tokyo
        (38.0, 150.0),   # Japan offshore
        (42.0, 160.0),   # North Pacific
        (45.0, 170.0),   # Aleutian approach
        (47.0, 180.0),   # Date line
        (47.0, -170.0),  # Past date line
        (45.0, -160.0),  # Central Pacific
        (43.0, -150.0),  # Eastern Pacific
        (40.0, -140.0),  # Off California
        (37.0, -125.0),  # San Francisco offshore
        (34.0, -120.0),  # Los Angeles approach
    ],

    # Pacific - Central route (Shanghai to LA)
    "pacific_central": [
        (30.0, 122.0),   # Off Shanghai
        (28.0, 125.0),   # East China Sea
        (25.0, 130.0),   # Off Japan South
        (22.0, 140.0),   # Western Pacific
        (20.0, 150.0),   # Pacific
        (18.0, 160.0),   # Mid Pacific
        (17.0, 170.0),   # Central Pacific
        (17.0, 180.0),   # Date line
        (18.0, -170.0),  # Past date line
        (20.0, -160.0),  # Hawaiian waters
        (22.0, -150.0),  # North of Hawaii
        (25.0, -140.0),  # Eastern Pacific
        (28.0, -130.0),  # Off Baja
        (32.0, -120.0),  # Off San Diego
        (33.8, -118.2),  # Los Angeles
    ],

    # Pacific - South route (to Panama/South America)
    "pacific_south": [
        (1.0, 104.0),    # Singapore Strait
        (-5.0, 110.0),   # Java Sea
        (-10.0, 120.0),  # Off Indonesia
        (-15.0, 135.0),  # Timor Sea
        (-18.0, 150.0),  # Coral Sea
        (-20.0, 165.0),  # New Caledonia
        (-18.0, 180.0),  # Fiji area
        (-15.0, -170.0), # South Pacific
        (-10.0, -150.0), # Eastern Pacific
        (-5.0, -130.0),  # Equatorial
        (0.0, -110.0),   # Galapagos area
        (5.0, -90.0),    # Panama approach
        (8.5, -79.5),    # Panama
    ],

    # ===========================================
    # CAPE OF GOOD HOPE ROUTE (Europe to Asia without Suez)
    # ===========================================

    "cape_europe_to_asia": [
        (50.0, -5.0),    # Western approaches UK
        (45.0, -10.0),   # Bay of Biscay
        (40.0, -10.0),   # Off Portugal
        (36.0, -8.0),    # Off Cape St Vincent
        (33.0, -10.0),   # Off Morocco
        (28.0, -15.0),   # Off Canaries
        (22.0, -18.0),   # Off Mauritania
        (15.0, -18.0),   # Off Senegal
        (10.0, -16.0),   # Off Guinea
        (5.0, -10.0),    # Off Liberia
        (0.0, -5.0),     # Gulf of Guinea West
        (-5.0, 5.0),     # Off Gabon
        (-10.0, 10.0),   # Off Angola
        (-20.0, 11.0),   # Off Namibia
        (-30.0, 15.0),   # Off South Africa West
        (-35.0, 19.0),   # Cape of Good Hope
        (-35.0, 25.0),   # Agulhas
        (-32.0, 32.0),   # Off Durban
        (-25.0, 38.0),   # Mozambique Channel
        (-15.0, 45.0),   # Off Madagascar
        (-10.0, 55.0),   # Indian Ocean
        (-5.0, 65.0),    # Central Indian Ocean
        (0.0, 75.0),     # Off Maldives
        (5.0, 85.0),     # Bay of Bengal
        (3.0, 95.0),     # Andaman Sea
        (1.5, 104.0),    # Singapore
    ],

    # ===========================================
    # MEDITERRANEAN SEA ROUTES
    # ===========================================

    "med_west_to_east": [
        (36.0, -5.5),   # Gibraltar Strait
        (36.2, -4.0),   # Alboran Sea
        (36.5, -2.0),   # Western Med
        (37.0, 0.0),    # Off Valencia
        (38.0, 2.0),    # Balearic Sea
        (38.5, 4.0),    # Off Sardinia
        (37.5, 7.0),    # Sicily Channel approach
        (36.5, 11.0),   # Sicily Strait
        (35.5, 14.5),   # Malta
        (35.0, 18.0),   # Ionian Sea
        (34.5, 22.0),   # Off Crete West
        (34.0, 26.0),   # Off Crete East
        (33.5, 30.0),   # Eastern Med
        (31.5, 32.0),   # Suez approach
    ],

    # English Channel / North Sea
    "channel_north_sea": [
        (49.5, -5.0),   # Western Channel approach
        (49.8, -3.0),   # Central Channel West
        (50.0, -1.0),   # Central Channel
        (50.5, 0.5),    # Dover Strait approach
        (51.0, 1.5),    # Dover Strait
        (51.5, 2.0),    # Southern North Sea
        (52.0, 3.0),    # Off Netherlands
        (52.5, 4.0),    # Rotterdam approach
        (53.0, 5.0),    # Off Frisian Islands
        (53.5, 6.0),    # German Bight West
        (54.0, 7.5),    # German Bight
        (54.5, 8.5),    # Hamburg approach
    ],

    # US East Coast
    "us_east_coast": [
        (40.5, -73.5),  # New York approach
        (39.5, -73.8),  # Off New Jersey
        (38.5, -74.5),  # Delaware Bay area
        (37.0, -75.5),  # Off Virginia
        (35.5, -75.0),  # Off North Carolina (wide berth around Hatteras)
        (34.0, -76.5),  # Off North Carolina South
        (32.5, -79.0),  # Charleston approach
        (31.0, -80.5),  # Off Georgia
        (29.5, -81.0),  # Off Florida
        (27.5, -80.0),  # Off Palm Beach
        (25.5, -80.0),  # Miami approach
    ],

    # Gulf of Mexico
    "gulf_mexico": [
        (25.0, -80.5),  # Florida Strait East
        (24.0, -82.0),  # Florida Strait Center
        (24.5, -84.0),  # Florida Strait West
        (25.5, -86.0),  # Central Gulf
        (27.0, -88.0),  # Northern Gulf
        (28.5, -89.0),  # Mississippi Delta approach
        (29.0, -89.5),  # New Orleans approach
    ],

    "gulf_to_houston": [
        (25.5, -86.0),  # Central Gulf
        (27.0, -92.0),  # Western Gulf
        (28.0, -94.0),  # Texas coast
        (28.8, -94.5),  # Houston approach
    ],

    # Caribbean
    "caribbean_main": [
        (18.0, -65.0),  # East Caribbean
        (17.5, -67.0),  # Puerto Rico South
        (16.5, -69.0),  # Dominican Republic
        (17.0, -72.0),  # Haiti/Jamaica passage
        (18.0, -75.0),  # Jamaica South
        (19.5, -78.0),  # Cuba South
        (21.0, -80.0),  # Yucatan Channel approach
    ],

    # US West Coast
    "us_west_coast": [
        (32.5, -117.5), # San Diego approach
        (33.5, -118.0), # Los Angeles approach
        (34.5, -120.5), # Santa Barbara Channel
        (36.0, -122.0), # Monterey Bay
        (37.5, -123.0), # San Francisco approach
        (40.0, -124.5), # Off Northern California
        (42.5, -125.0), # Off Oregon
        (45.0, -124.5), # Columbia River approach
        (47.0, -125.0), # Off Washington
        (48.0, -125.0), # Juan de Fuca approach
        (48.2, -123.5), # Seattle approach
    ],

    # Trans-Pacific (simplified - major waypoints)
    "pacific_crossing_north": [
        (35.0, 140.0),  # Japan East
        (38.0, 150.0),  # North Pacific
        (40.0, 160.0),
        (42.0, 170.0),
        (43.0, 180.0),  # Date line
        (42.0, -170.0),
        (40.0, -160.0),
        (38.0, -150.0),
        (36.0, -140.0),
        (34.0, -130.0),
        (33.5, -120.0), # California approach
    ],

    # South China Sea
    "south_china_sea": [
        (1.5, 104.0),   # Singapore Strait East
        (3.0, 106.0),   # Off Borneo
        (6.0, 110.0),   # Central South China Sea
        (10.0, 113.0),  # Off Vietnam
        (14.0, 116.0),  # Northern SCS
        (18.0, 117.0),  # Off Philippines/Luzon Strait approach
        (22.0, 114.0),  # Hong Kong approach
    ],

    # Singapore to Hong Kong direct
    "singapore_hongkong": [
        (1.3, 103.8),   # Singapore
        (3.0, 105.0),
        (6.0, 107.0),
        (10.0, 110.0),
        (14.0, 112.5),
        (18.0, 114.5),
        (22.0, 114.2),  # Hong Kong
    ],

    # Japan/Korea
    "japan_korea": [
        (35.0, 129.5),  # Korea Strait
        (34.0, 131.0),  # Off Japan
        (33.5, 133.0),  # Inland Sea approach
        (34.0, 135.0),  # Osaka Bay
        (34.5, 137.0),  # Off Honshu
        (35.0, 139.5),  # Tokyo Bay approach
    ],

    # Suez to Persian Gulf
    "suez_to_gulf": [
        (29.9, 32.5),   # Suez South
        (27.5, 34.0),   # Red Sea North
        (24.0, 36.0),   # Central Red Sea
        (20.0, 38.5),   # Southern Red Sea
        (15.0, 42.0),   # Bab el-Mandeb North
        (12.5, 43.5),   # Bab el-Mandeb
        (13.0, 48.0),   # Gulf of Aden
        (15.0, 53.0),   # Arabian Sea West
        (18.0, 57.0),   # Off Oman
        (22.0, 59.0),   # Oman Coast
        (25.0, 57.0),   # Hormuz approach
        (26.5, 56.5),   # Strait of Hormuz
        (27.0, 52.0),   # Persian Gulf
        (29.0, 49.0),   # Kuwait approach
    ],

    # Indian Ocean to Suez
    "indian_to_suez": [
        (6.0, 80.0),    # Off Sri Lanka
        (10.0, 72.0),   # Arabian Sea
        (12.0, 60.0),   # Central Arabian Sea
        (12.5, 50.0),   # Gulf of Aden East
        (12.5, 43.5),   # Bab el-Mandeb
        (15.0, 42.0),   # Red Sea South
        (20.0, 38.5),   # Central Red Sea
        (27.5, 34.0),   # Red Sea North
        (29.9, 32.5),   # Suez
    ],

    # Mumbai route
    "mumbai_route": [
        (18.9, 72.8),   # Mumbai
        (16.0, 70.0),   # Off India West
        (12.0, 65.0),   # Arabian Sea
        (10.0, 60.0),   # Central Arabian Sea
    ],

    # Cape of Good Hope route
    "cape_route": [
        (-34.0, 18.5),  # Cape Town
        (-35.0, 20.0),  # Cape of Good Hope
        (-34.0, 25.0),  # Off South Africa East
        (-32.0, 29.0),  # Off KwaZulu-Natal
        (-30.0, 32.0),  # Durban approach
    ],

    # Australia
    "australia_route": [
        (-34.0, 151.0), # Sydney approach
        (-36.0, 150.0), # Off NSW
        (-38.0, 148.0), # Bass Strait East
        (-39.0, 145.0), # Bass Strait
        (-38.0, 145.0), # Melbourne approach
    ],

    # South America East
    "south_america_east": [
        (-24.0, -46.0), # Santos approach
        (-28.0, -48.0), # Off Brazil South
        (-32.0, -51.0), # Off Uruguay
        (-35.0, -56.0), # Rio de la Plata approach
    ],

    # South America West
    "south_america_west": [
        (-33.0, -72.0), # Valparaiso
        (-30.0, -72.0), # Off Chile
        (-25.0, -71.0), # Northern Chile
        (-18.0, -71.0), # Peru approach
    ],

    # Panama approaches
    "panama_caribbean": [
        (9.5, -79.5),   # Panama Caribbean side
        (11.0, -79.0),  # Off Panama
        (13.0, -78.0),  # Off Colombia
        (15.0, -76.0),  # Caribbean
    ],

    "panama_pacific": [
        (8.5, -79.5),   # Panama Pacific side
        (7.0, -80.0),   # Off Panama
        (5.0, -81.0),   # Off Ecuador
        (0.0, -82.0),   # Equator
    ],
}

# COMMAND ----------

# Vessel definitions with their assigned shipping lanes
# NOTE: Vessels should ONLY use routes that stay entirely in the ocean!
SYNTHETIC_VESSELS = [
    # ===========================================
    # TRANS-ATLANTIC ROUTES (Europe <-> Americas)
    # ===========================================
    {"mmsi": "244650123", "name": "MAERSK SEALAND", "ship_type": 70, "flag": "NL",
     "lanes": ["atlantic_north_eu_us"], "speed": 18.5, "dest": "NEW YORK"},
    {"mmsi": "636091234", "name": "MSC GENEVA", "ship_type": 70, "flag": "LR",
     "lanes": ["atlantic_north_us_eu"], "speed": 16.2, "dest": "ROTTERDAM"},
    {"mmsi": "538006789", "name": "COSCO SHIPPING", "ship_type": 70, "flag": "MH",
     "lanes": ["atlantic_south_eu_brazil"], "speed": 14.8, "dest": "SANTOS"},

    # English Channel / North Sea (regional only)
    {"mmsi": "235089012", "name": "DOVER SPIRIT", "ship_type": 60, "flag": "GB",
     "lanes": ["channel_north_sea"], "speed": 12.5, "dest": "CALAIS"},
    {"mmsi": "227345678", "name": "NORMANDIE EXPRESS", "ship_type": 60, "flag": "FR",
     "lanes": ["channel_north_sea"], "speed": 22.0, "dest": "LE HAVRE"},
    {"mmsi": "211234567", "name": "HAMBURG BRIDGE", "ship_type": 70, "flag": "DE",
     "lanes": ["channel_north_sea"], "speed": 15.3, "dest": "HAMBURG"},
    {"mmsi": "245678901", "name": "ROTTERDAM EXPRESS", "ship_type": 70, "flag": "NL",
     "lanes": ["channel_north_sea"], "speed": 11.2, "dest": "ROTTERDAM"},

    # US East Coast (regional only)
    {"mmsi": "367890123", "name": "ATLANTIC STAR", "ship_type": 70, "flag": "US",
     "lanes": ["us_east_coast"], "speed": 8.5, "dest": "NEW YORK"},
    {"mmsi": "368012345", "name": "CHARLESTON CARRIER", "ship_type": 70, "flag": "US",
     "lanes": ["us_east_coast"], "speed": 10.2, "dest": "CHARLESTON"},
    {"mmsi": "338123456", "name": "MIAMI TRADER", "ship_type": 70, "flag": "US",
     "lanes": ["us_east_coast"], "speed": 12.0, "dest": "MIAMI"},

    # Gulf of Mexico (regional)
    {"mmsi": "367234567", "name": "GULF PIONEER", "ship_type": 80, "flag": "US",
     "lanes": ["gulf_mexico"], "speed": 6.5, "dest": "NEW ORLEANS"},
    {"mmsi": "345678012", "name": "HOUSTON OIL", "ship_type": 80, "flag": "PA",
     "lanes": ["gulf_to_houston"], "speed": 8.0, "dest": "HOUSTON"},

    # Caribbean (regional)
    {"mmsi": "352345678", "name": "CARIBBEAN QUEEN", "ship_type": 60, "flag": "PA",
     "lanes": ["caribbean_main"], "speed": 15.5, "dest": "SAN JUAN"},
    {"mmsi": "309456789", "name": "BAHAMAS EXPRESS", "ship_type": 60, "flag": "BS",
     "lanes": ["us_east_coast"], "speed": 18.0, "dest": "NASSAU"},

    # ===========================================
    # TRANS-PACIFIC ROUTES (Asia <-> Americas)
    # ===========================================
    {"mmsi": "366789012", "name": "PACIFIC NAVIGATOR", "ship_type": 70, "flag": "US",
     "lanes": ["pacific_asia_us_north"], "speed": 14.5, "dest": "LOS ANGELES"},
    {"mmsi": "369012345", "name": "OAKLAND BRIDGE", "ship_type": 70, "flag": "US",
     "lanes": ["pacific_central"], "speed": 10.0, "dest": "OAKLAND"},
    {"mmsi": "367345678", "name": "SEATTLE TRADER", "ship_type": 70, "flag": "US",
     "lanes": ["us_west_coast"], "speed": 8.5, "dest": "SEATTLE"},

    # Asia Regional - South China Sea
    {"mmsi": "413456789", "name": "SHANGHAI EXPRESS", "ship_type": 70, "flag": "CN",
     "lanes": ["pacific_central"], "speed": 16.8, "dest": "LOS ANGELES"},
    {"mmsi": "416789012", "name": "SHENZHEN STAR", "ship_type": 70, "flag": "CN",
     "lanes": ["singapore_hongkong"], "speed": 18.2, "dest": "HONG KONG"},
    {"mmsi": "533012345", "name": "SINGAPORE SPIRIT", "ship_type": 70, "flag": "SG",
     "lanes": ["singapore_hongkong"], "speed": 12.5, "dest": "SINGAPORE"},
    {"mmsi": "548234567", "name": "MANILA BAY", "ship_type": 70, "flag": "PH",
     "lanes": ["south_china_sea"], "speed": 11.0, "dest": "MANILA"},

    # Japan/Korea (regional)
    {"mmsi": "431567890", "name": "TOKYO MARU", "ship_type": 70, "flag": "JP",
     "lanes": ["japan_korea"], "speed": 14.0, "dest": "TOKYO"},
    {"mmsi": "440678901", "name": "BUSAN CONTAINER", "ship_type": 70, "flag": "KR",
     "lanes": ["japan_korea"], "speed": 15.5, "dest": "BUSAN"},

    # ===========================================
    # SUEZ / RED SEA / PERSIAN GULF
    # ===========================================
    {"mmsi": "470789012", "name": "DUBAI MERCHANT", "ship_type": 80, "flag": "AE",
     "lanes": ["suez_to_gulf"], "speed": 10.5, "dest": "DUBAI"},
    {"mmsi": "622890123", "name": "SUEZ TRANSPORTER", "ship_type": 70, "flag": "EG",
     "lanes": ["suez_to_gulf"], "speed": 8.0, "dest": "PORT SAID"},
    {"mmsi": "403901234", "name": "PERSIAN GULF", "ship_type": 80, "flag": "SA",
     "lanes": ["suez_to_gulf"], "speed": 12.0, "dest": "DAMMAM"},

    # Indian Ocean
    {"mmsi": "419012345", "name": "MUMBAI CARRIER", "ship_type": 70, "flag": "IN",
     "lanes": ["indian_to_suez"], "speed": 13.5, "dest": "MUMBAI"},
    {"mmsi": "565123456", "name": "COLOMBO TRADER", "ship_type": 70, "flag": "LK",
     "lanes": ["indian_to_suez"], "speed": 11.0, "dest": "COLOMBO"},

    # ===========================================
    # CAPE OF GOOD HOPE ROUTE (long haul around Africa)
    # ===========================================
    {"mmsi": "601234567", "name": "CAPE TOWN EXPRESS", "ship_type": 70, "flag": "ZA",
     "lanes": ["africa_west_coast"], "speed": 14.0, "dest": "CAPE TOWN"},
    {"mmsi": "627345678", "name": "DURBAN STAR", "ship_type": 70, "flag": "ZA",
     "lanes": ["cape_route"], "speed": 12.5, "dest": "DURBAN"},
    {"mmsi": "538998877", "name": "CAPE VOYAGER", "ship_type": 70, "flag": "MH",
     "lanes": ["cape_europe_to_asia"], "speed": 15.0, "dest": "SINGAPORE"},

    # Australia (regional)
    {"mmsi": "503456789", "name": "SYDNEY HARBOUR", "ship_type": 70, "flag": "AU",
     "lanes": ["australia_route"], "speed": 10.0, "dest": "SYDNEY"},
    {"mmsi": "503567890", "name": "MELBOURNE TRADER", "ship_type": 70, "flag": "AU",
     "lanes": ["australia_route"], "speed": 11.5, "dest": "MELBOURNE"},

    # South America (regional)
    {"mmsi": "710678901", "name": "SANTOS PIONEER", "ship_type": 70, "flag": "BR",
     "lanes": ["south_america_east"], "speed": 13.0, "dest": "SANTOS"},
    {"mmsi": "725789012", "name": "BUENOS AIRES", "ship_type": 70, "flag": "AR",
     "lanes": ["south_america_east"], "speed": 9.5, "dest": "BUENOS AIRES"},
    {"mmsi": "730890123", "name": "VALPARAISO STAR", "ship_type": 70, "flag": "CL",
     "lanes": ["south_america_west"], "speed": 12.0, "dest": "VALPARAISO"},

    # Panama Canal approaches (regional)
    {"mmsi": "352901234", "name": "CANAL NAVIGATOR", "ship_type": 70, "flag": "PA",
     "lanes": ["panama_caribbean"], "speed": 8.0, "dest": "PANAMA"},

    # Mediterranean (regional)
    {"mmsi": "538112233", "name": "MED CRUISER", "ship_type": 70, "flag": "MH",
     "lanes": ["med_west_to_east"], "speed": 12.0, "dest": "PIRAEUS"},
    {"mmsi": "538223344", "name": "SICILY EXPRESS", "ship_type": 70, "flag": "MH",
     "lanes": ["med_west_to_east"], "speed": 14.5, "dest": "MALTA"},
    {"mmsi": "477334455", "name": "ADRIATIC SPIRIT", "ship_type": 70, "flag": "IT",
     "lanes": ["med_west_to_east"], "speed": 13.0, "dest": "SUEZ"},
]

# COMMAND ----------

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in nautical miles between two points."""
    # Haversine formula
    R = 3440.065  # Earth's radius in nautical miles
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def interpolate_position(lat1, lon1, lat2, lon2, fraction):
    """Interpolate between two positions."""
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points in degrees."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def create_dense_route(lane_names, reverse=False):
    """Create a dense route by combining lane waypoints."""
    all_waypoints = []

    for lane_name in lane_names:
        if lane_name in SHIPPING_LANES:
            lane = SHIPPING_LANES[lane_name]
            if reverse:
                lane = list(reversed(lane))
            all_waypoints.extend(lane)

    if not all_waypoints:
        return []

    # Interpolate between waypoints for smoother routes
    dense_route = []
    for i in range(len(all_waypoints) - 1):
        lat1, lon1 = all_waypoints[i]
        lat2, lon2 = all_waypoints[i + 1]

        # Calculate distance and add intermediate points
        dist = calculate_distance(lat1, lon1, lat2, lon2)

        # Add a point roughly every 50 nautical miles
        num_points = max(1, int(dist / 50))

        for j in range(num_points):
            fraction = j / num_points
            lat, lon = interpolate_position(lat1, lon1, lat2, lon2, fraction)
            dense_route.append((lat, lon))

    # Add the final point
    dense_route.append(all_waypoints[-1])

    return dense_route

def generate_vessel_route(vessel, days, interval_hours):
    """Generate historical positions for a vessel following its assigned shipping lanes."""
    positions = []

    # Get the route waypoints
    route = create_dense_route(vessel["lanes"], reverse=random.choice([True, False]))

    if not route:
        return []

    # Start at a random position along the route
    route_length = len(route)
    start_idx = random.randint(0, max(0, route_length - 1))

    # Calculate total positions needed
    total_hours = days * 24
    num_positions = total_hours // interval_hours

    now = datetime.utcnow()
    speed_kts = vessel["speed"]

    # Track position along route
    current_idx = start_idx
    progress_in_segment = 0.0  # 0 to 1 within current segment
    direction = 1  # 1 = forward, -1 = backward

    for pos_num in range(num_positions):
        # Calculate time for this position
        hours_back = pos_num * interval_hours
        time_at_position = now - timedelta(hours=hours_back)

        # Get current and next waypoint
        if current_idx >= route_length - 1:
            direction = -1
            current_idx = route_length - 2
        elif current_idx <= 0:
            direction = 1
            current_idx = 0

        next_idx = current_idx + direction
        if next_idx < 0 or next_idx >= route_length:
            next_idx = current_idx

        lat1, lon1 = route[current_idx]
        lat2, lon2 = route[next_idx]

        # Interpolate position
        lat, lon = interpolate_position(lat1, lon1, lat2, lon2, progress_in_segment)

        # Add small random variation (but not enough to go over land)
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)

        # Calculate course to next waypoint
        course = calculate_bearing(lat, lon, lat2, lon2)

        # Add speed variation
        actual_speed = max(5, speed_kts + random.uniform(-2, 2))

        positions.append({
            "latitude": lat,
            "longitude": lon,
            "speed": actual_speed,
            "course": course,
            "recorded_at": time_at_position,
        })

        # Move along the route
        segment_dist = calculate_distance(lat1, lon1, lat2, lon2)
        if segment_dist > 0:
            distance_per_interval = actual_speed * interval_hours
            progress_per_interval = distance_per_interval / segment_dist
            progress_in_segment += progress_per_interval * direction

            # Move to next segment if needed
            while progress_in_segment >= 1.0:
                progress_in_segment -= 1.0
                current_idx += direction
                if current_idx >= route_length - 1:
                    direction = -1
                    current_idx = route_length - 2
                    break

            while progress_in_segment < 0.0:
                progress_in_segment += 1.0
                current_idx += direction
                if current_idx <= 0:
                    direction = 1
                    current_idx = 0
                    break

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
# MAGIC Generated vessel position history with ACCURATE OCEAN ROUTES:
# MAGIC - **Vessels**: 39 synthetic vessels
# MAGIC - **Days of history**: 30 days
# MAGIC - **Interval**: Every 4 hours
# MAGIC - **Total positions**: ~7,000 records
# MAGIC
# MAGIC Routes now follow dense waypoint sequences in actual shipping lanes:
# MAGIC - Mediterranean Sea (Gibraltar to Suez)
# MAGIC - English Channel / North Sea
# MAGIC - US East Coast (New York to Miami)
# MAGIC - Gulf of Mexico
# MAGIC - Caribbean
# MAGIC - US West Coast (San Diego to Seattle)
# MAGIC - South China Sea (Singapore to Hong Kong)
# MAGIC - Japan/Korea Strait
# MAGIC - Suez to Persian Gulf (Red Sea, Bab el-Mandeb, Arabian Sea)
# MAGIC - Indian Ocean routes
# MAGIC - Cape of Good Hope
# MAGIC - Australia (Sydney to Melbourne via Bass Strait)
# MAGIC - South America (Santos, Buenos Aires, Valparaiso)
# MAGIC - Panama Canal approaches

# COMMAND ----------

# Show sample routes
sample_vessel = "999000000"  # First vessel
sample_df = df.filter(df.mmsi == sample_vessel).orderBy("recorded_at")
print(f"Sample route for {sample_vessel}:")
display(sample_df.select("recorded_at", "latitude", "longitude", "speed", "course").limit(20))
