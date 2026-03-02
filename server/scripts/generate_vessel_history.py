"""
Generate 30 days of historical vessel position data for demo purposes.

Creates realistic vessel routes that:
- Stay in navigable waters
- Follow major shipping lanes
- Connect to known port locations
- Have realistic speed/course variations

Run with: python -m server.scripts.generate_vessel_history
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Optional

# Major shipping waypoints to keep vessels in water
WAYPOINTS = {
    # Mediterranean Sea
    "gibraltar": (36.1, -5.4),
    "sicily_strait": (37.0, 11.5),
    "malta": (35.9, 14.4),
    "crete_south": (34.8, 24.5),
    "suez_north": (31.2, 32.3),
    "suez_south": (29.9, 32.5),

    # English Channel / North Sea
    "dover": (51.1, 1.3),
    "calais": (50.9, 1.8),
    "rotterdam_approach": (52.0, 3.8),
    "hamburg_approach": (54.0, 8.3),

    # Atlantic - US East Coast
    "new_york_approach": (40.4, -73.5),
    "charleston_approach": (32.6, -79.5),
    "miami_approach": (25.7, -80.0),
    "florida_strait": (24.5, -81.5),

    # Gulf of Mexico
    "gulf_center": (27.0, -90.0),
    "new_orleans_approach": (29.0, -89.2),
    "houston_approach": (29.0, -94.5),

    # Caribbean
    "windward_passage": (19.8, -73.5),
    "mona_passage": (18.5, -67.5),
    "puerto_rico_north": (18.8, -66.0),

    # Pacific - US West Coast
    "la_approach": (33.5, -118.0),
    "sf_approach": (37.6, -122.5),
    "seattle_approach": (48.0, -124.5),

    # Asia - South China Sea
    "hong_kong": (22.2, 114.1),
    "taiwan_strait": (24.0, 119.5),
    "luzon_strait": (20.0, 121.0),
    "singapore_strait": (1.2, 103.9),
    "malacca_north": (5.8, 100.0),
    "malacca_south": (1.5, 102.5),

    # Japan/Korea
    "tokyo_bay": (35.3, 139.7),
    "tsushima_strait": (34.0, 129.5),
    "korea_strait": (34.5, 128.5),

    # Middle East
    "hormuz": (26.5, 56.5),
    "bab_el_mandeb": (12.6, 43.4),
    "gulf_of_aden": (12.0, 47.0),
    "arabian_sea": (15.0, 60.0),

    # Indian Ocean
    "mumbai_approach": (18.8, 72.7),
    "colombo_approach": (6.8, 79.8),
    "cape_good_hope": (-34.5, 18.5),
    "agulhas": (-35.0, 20.0),

    # Australia
    "sydney_approach": (-33.7, 151.3),
    "melbourne_approach": (-38.0, 144.5),
    "bass_strait": (-39.5, 146.0),

    # South America
    "rio_approach": (-23.0, -43.0),
    "santos_approach": (-24.0, -46.0),
    "buenos_aires_approach": (-35.0, -57.0),
    "cape_horn": (-56.0, -67.0),
    "valparaiso_approach": (-33.2, -71.8),

    # Panama
    "panama_pacific": (8.9, -79.6),
    "panama_atlantic": (9.4, -79.9),
}

# Route templates: vessel destination -> waypoints to follow backwards
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
    "SAN JUAN": ["puerto_rico_north", "mona_passage"],
    "NASSAU": ["florida_strait"],
    "LOS ANGELES": ["la_approach"],
    "OAKLAND": ["sf_approach"],
    "SEATTLE": ["seattle_approach", "sf_approach"],
    "HONG KONG": ["hong_kong", "taiwan_strait"],
    "SHENZHEN": ["hong_kong"],
    "SINGAPORE": ["singapore_strait", "malacca_south"],
    "MANILA": ["luzon_strait", "taiwan_strait"],
    "TOKYO": ["tokyo_bay", "tsushima_strait"],
    "BUSAN": ["korea_strait"],
    "DUBAI": ["hormuz", "arabian_sea"],
    "PORT SAID": ["suez_north"],
    "DAMMAM": ["hormuz"],
    "MUMBAI": ["mumbai_approach", "arabian_sea"],
    "COLOMBO": ["colombo_approach"],
    "CAPE TOWN": ["cape_good_hope", "agulhas"],
    "DURBAN": ["agulhas"],
    "SYDNEY": ["sydney_approach"],
    "MELBOURNE": ["melbourne_approach", "bass_strait"],
    "SANTOS": ["santos_approach", "rio_approach"],
    "BUENOS AIRES": ["buenos_aires_approach", "rio_approach"],
    "VALPARAISO": ["valparaiso_approach"],
    "PANAMA": ["panama_pacific"],
    "BAB EL MANDEB": ["bab_el_mandeb", "gulf_of_aden"],
    "KUWAIT": ["hormuz"],
    "VUNG TAU": ["singapore_strait"],
}


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing between two points in degrees."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def move_point(lat: float, lon: float, bearing: float, distance_nm: float) -> tuple[float, float]:
    """Move a point by distance (nautical miles) along a bearing."""
    # 1 degree latitude = 60 nm
    # 1 degree longitude = 60 nm * cos(lat)
    distance_deg = distance_nm / 60.0

    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)

    new_lat = lat + distance_deg * math.cos(bearing_rad)
    new_lon = lon + distance_deg * math.sin(bearing_rad) / max(math.cos(lat_rad), 0.1)

    return new_lat, new_lon


def generate_vessel_route(
    current_lat: float,
    current_lon: float,
    destination: str,
    speed_kts: float,
    days: int = 30,
    interval_hours: float = 4,
) -> list[dict]:
    """Generate historical positions for a vessel going backwards in time.

    Returns list of positions from oldest to newest.
    """
    positions = []

    # Get waypoints for this route
    waypoints = ROUTE_TEMPLATES.get(destination, [])
    waypoint_coords = [(current_lat, current_lon)]  # Start at current position

    for wp_name in waypoints:
        if wp_name in WAYPOINTS:
            waypoint_coords.append(WAYPOINTS[wp_name])

    # Calculate total distance needed for 30 days at current speed
    total_hours = days * 24
    total_distance_nm = speed_kts * total_hours

    # Generate positions going backwards in time
    now = datetime.utcnow()
    current_pos = (current_lat, current_lon)
    current_wp_idx = 0

    hours_back = 0
    while hours_back < total_hours:
        # Add some speed variation
        actual_speed = speed_kts + random.uniform(-2, 2)
        actual_speed = max(5, actual_speed)  # Minimum 5 knots

        # Calculate where vessel was at this time
        time_at_position = now - timedelta(hours=hours_back)

        # Determine bearing to next waypoint or continue on course
        if current_wp_idx < len(waypoint_coords) - 1:
            next_wp = waypoint_coords[current_wp_idx + 1]
            bearing = calculate_bearing(current_pos[0], current_pos[1], next_wp[0], next_wp[1])

            # Check if we've passed the waypoint (going backwards, so opposite direction)
            reverse_bearing = (bearing + 180) % 360
        else:
            # No more waypoints, continue on a reasonable course
            reverse_bearing = random.uniform(0, 360)

        # Add some course variation
        course_variation = random.uniform(-10, 10)
        actual_bearing = (reverse_bearing + course_variation) % 360

        # Move backwards along the route
        distance_traveled = actual_speed * interval_hours
        new_lat, new_lon = move_point(current_pos[0], current_pos[1], actual_bearing, distance_traveled)

        # Keep within reasonable bounds
        new_lat = max(-85, min(85, new_lat))
        new_lon = max(-180, min(180, new_lon))

        positions.append({
            "latitude": new_lat,
            "longitude": new_lon,
            "speed": actual_speed,
            "course": (actual_bearing + 180) % 360,  # Course is forward direction
            "recorded_at": time_at_position,
        })

        current_pos = (new_lat, new_lon)
        hours_back += interval_hours

        # Check if we've reached a waypoint
        if current_wp_idx < len(waypoint_coords) - 1:
            next_wp = waypoint_coords[current_wp_idx + 1]
            dist_to_wp = math.sqrt((current_pos[0] - next_wp[0])**2 + (current_pos[1] - next_wp[1])**2)
            if dist_to_wp < 1:  # Within ~60nm of waypoint
                current_wp_idx += 1

    # Return in chronological order (oldest first)
    positions.reverse()
    return positions


async def generate_all_vessel_history():
    """Generate 30 days of historical data for all synthetic vessels."""
    # Import here to avoid circular imports
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    from server.routes.maritime import SYNTHETIC_VESSELS
    from server.db import db, init_vessel_positions_table
    from server.config import settings

    if not settings.is_lakebase_configured():
        print("Lakebase not configured. Cannot generate historical data.")
        print("Set PGHOST, PGDATABASE, PGUSER environment variables.")
        return

    # Initialize database
    await db.get_pool()
    await init_vessel_positions_table()

    print(f"Generating 30 days of historical data for {len(SYNTHETIC_VESSELS)} vessels...")

    total_positions = 0

    for idx, vessel in enumerate(SYNTHETIC_VESSELS):
        synthetic_mmsi = f"999{idx:06d}"

        print(f"  [{idx+1}/{len(SYNTHETIC_VESSELS)}] {vessel['name']} ({synthetic_mmsi})...")

        # Generate route history
        positions = generate_vessel_route(
            current_lat=vessel["lat"],
            current_lon=vessel["lon"],
            destination=vessel["dest"],
            speed_kts=vessel["speed"],
            days=30,
            interval_hours=4,  # Position every 4 hours
        )

        # Save to database
        if positions:
            try:
                async with db.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO vessel_positions
                        (mmsi, name, ship_type, flag_country, latitude, longitude,
                         speed, course, heading, destination, is_synthetic, recorded_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        """,
                        [
                            (
                                synthetic_mmsi,
                                f"{vessel['name']} [DEMO]",
                                vessel["ship_type"],
                                vessel["flag"],
                                p["latitude"],
                                p["longitude"],
                                p["speed"],
                                p["course"],
                                int(p["course"]),
                                vessel["dest"],
                                True,
                                p["recorded_at"],
                            )
                            for p in positions
                        ]
                    )
                total_positions += len(positions)
                print(f"    Saved {len(positions)} positions")
            except Exception as e:
                print(f"    Error saving positions: {e}")

    print(f"\nTotal positions generated: {total_positions}")
    print("Done!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(generate_all_vessel_history())
