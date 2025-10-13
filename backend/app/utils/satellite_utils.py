"""
Utility functions for satellite data processing and validation.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import math

def validate_norad_id(norad_id: int) -> bool:
    """
    Validate NORAD ID format and range.
    
    Args:
        norad_id: NORAD catalog number
        
    Returns:
        True if valid, False otherwise
    """
    # NORAD IDs are typically 5-digit numbers, but can be up to 6 digits
    return isinstance(norad_id, int) and 1 <= norad_id <= 999999


def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, Optional[str]]:
    """
    Validate geographic coordinates.
    
    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(latitude, (int, float, Decimal)):
        return False, "Latitude must be a number"
    
    if not isinstance(longitude, (int, float, Decimal)):
        return False, "Longitude must be a number"
    
    lat = float(latitude)
    lng = float(longitude)
    
    if not (-90 <= lat <= 90):
        return False, "Latitude must be between -90 and 90 degrees"
    
    if not (-180 <= lng <= 180):
        return False, "Longitude must be between -180 and 180 degrees"
    
    return True, None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    Uses the Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates in degrees
        lat2, lon2: Second point coordinates in degrees
        
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    earth_radius = 6371.0
    
    return earth_radius * c


def calculate_elevation_angle(satellite_lat: float, satellite_lon: float, satellite_alt: float,
                            observer_lat: float, observer_lon: float, observer_alt: float = 0) -> float:
    """
    Calculate the elevation angle of a satellite as seen from an observer.
    
    Args:
        satellite_lat: Satellite latitude in degrees
        satellite_lon: Satellite longitude in degrees
        satellite_alt: Satellite altitude in kilometers
        observer_lat: Observer latitude in degrees
        observer_lon: Observer longitude in degrees
        observer_alt: Observer altitude in kilometers
        
    Returns:
        Elevation angle in degrees
    """
    # Convert to radians
    sat_lat_rad = math.radians(satellite_lat)
    sat_lon_rad = math.radians(satellite_lon)
    obs_lat_rad = math.radians(observer_lat)
    obs_lon_rad = math.radians(observer_lon)
    
    # Earth's radius in kilometers
    earth_radius = 6371.0
    
    # Calculate satellite position in 3D space
    sat_x = (earth_radius + satellite_alt) * math.cos(sat_lat_rad) * math.cos(sat_lon_rad)
    sat_y = (earth_radius + satellite_alt) * math.cos(sat_lat_rad) * math.sin(sat_lon_rad)
    sat_z = (earth_radius + satellite_alt) * math.sin(sat_lat_rad)
    
    # Calculate observer position in 3D space
    obs_x = (earth_radius + observer_alt) * math.cos(obs_lat_rad) * math.cos(obs_lon_rad)
    obs_y = (earth_radius + observer_alt) * math.cos(obs_lat_rad) * math.sin(obs_lon_rad)
    obs_z = (earth_radius + observer_alt) * math.sin(obs_lat_rad)
    
    # Vector from observer to satellite
    dx = sat_x - obs_x
    dy = sat_y - obs_y
    dz = sat_z - obs_z
    
    # Distance to satellite
    distance = math.sqrt(dx**2 + dy**2 + dz**2)
    
    # Local horizon vector (perpendicular to Earth's surface at observer)
    horizon_x = math.cos(obs_lat_rad) * math.cos(obs_lon_rad)
    horizon_y = math.cos(obs_lat_rad) * math.sin(obs_lon_rad)
    horizon_z = math.sin(obs_lat_rad)
    
    # Dot product to find angle
    dot_product = (dx * horizon_x + dy * horizon_y + dz * horizon_z) / distance
    
    # Elevation angle
    elevation = math.degrees(math.asin(dot_product))
    
    return elevation


def format_satellite_name(name: str) -> str:
    """
    Format satellite name for consistent display.
    
    Args:
        name: Raw satellite name
        
    Returns:
        Formatted satellite name
    """
    if not name:
        return "Unknown Satellite"
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Common formatting improvements
    name = name.replace('(', ' (').replace(')', ') ')
    name = re.sub(r'\s+', ' ', name.strip())
    
    return name


def categorize_satellite(name: str) -> str:
    """
    Attempt to categorize a satellite based on its name.
    
    Args:
        name: Satellite name
        
    Returns:
        Satellite category
    """
    name_upper = name.upper()
    
    # Space stations
    if any(keyword in name_upper for keyword in ['ISS', 'SPACE STATION', 'TIANGONG']):
        return "Space Stations"
    
    # Weather satellites
    if any(keyword in name_upper for keyword in ['NOAA', 'GOES', 'METOP', 'WEATHER']):
        return "Weather"
    
    # Communication satellites
    if any(keyword in name_upper for keyword in ['INTELSAT', 'EUTELSAT', 'ASTRA', 'HOTBIRD', 'STARLINK']):
        return "Communications"
    
    # Navigation satellites
    if any(keyword in name_upper for keyword in ['GPS', 'GLONASS', 'GALILEO', 'BEIDOU', 'NAVSTAR']):
        return "Navigation"
    
    # Earth observation
    if any(keyword in name_upper for keyword in ['LANDSAT', 'SENTINEL', 'TERRA', 'AQUA', 'MODIS']):
        return "Earth Observation"
    
    # Scientific satellites
    if any(keyword in name_upper for keyword in ['HUBBLE', 'CHANDRA', 'SPITZER', 'KEPLER', 'TESS']):
        return "Scientific"
    
    # Military satellites
    if any(keyword in name_upper for keyword in ['MILSTAR', 'DSCS', 'AEHF', 'WGS']):
        return "Military"
    
    # Amateur radio
    if any(keyword in name_upper for keyword in ['AMSAT', 'AO-', 'FO-', 'SO-', 'OSCAR']):
        return "Amateur Radio"
    
    return "Other"


def is_satellite_visible(elevation: float, magnitude: Optional[float] = None) -> bool:
    """
    Determine if a satellite is visible to the naked eye.
    
    Args:
        elevation: Elevation angle in degrees
        magnitude: Visual magnitude (lower is brighter)
        
    Returns:
        True if satellite is likely visible
    """
    # Must be above horizon
    if elevation <= 0:
        return False
    
    # If magnitude is available, use it for visibility determination
    if magnitude is not None:
        # Magnitude 6.5 is roughly the limit of naked eye visibility
        return magnitude <= 6.5
    
    # Without magnitude, assume visible if elevation is reasonable
    return elevation >= 10  # At least 10 degrees above horizon


def filter_passes_by_visibility(passes: List[Dict], min_elevation: float = 10.0) -> List[Dict]:
    """
    Filter satellite passes by minimum elevation for visibility.
    
    Args:
        passes: List of pass dictionaries
        min_elevation: Minimum elevation angle in degrees
        
    Returns:
        Filtered list of visible passes
    """
    visible_passes = []
    
    for pass_data in passes:
        max_elevation = float(pass_data.get("max_elevation", 0))
        
        if max_elevation >= min_elevation:
            # Add visibility flag
            pass_data["is_visible"] = is_satellite_visible(
                max_elevation, 
                float(pass_data.get("magnitude")) if pass_data.get("magnitude") else None
            )
            visible_passes.append(pass_data)
    
    return visible_passes


def sort_passes_by_time(passes: List[Dict]) -> List[Dict]:
    """
    Sort satellite passes by start time.
    
    Args:
        passes: List of pass dictionaries
        
    Returns:
        Sorted list of passes
    """
    return sorted(passes, key=lambda x: x.get("start_time", datetime.min))


def get_next_pass(passes: List[Dict]) -> Optional[Dict]:
    """
    Get the next upcoming pass from a list of passes.
    
    Args:
        passes: List of pass dictionaries
        
    Returns:
        Next pass dictionary or None if no upcoming passes
    """
    now = datetime.utcnow()
    
    upcoming_passes = [
        pass_data for pass_data in passes 
        if pass_data.get("start_time", datetime.min) > now
    ]
    
    if not upcoming_passes:
        return None
    
    return min(upcoming_passes, key=lambda x: x.get("start_time", datetime.min))


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def validate_satellite_data(data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate satellite data structure and required fields.
    
    Args:
        data: Satellite data dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    required_fields = ["norad_id", "name"]
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Validate NORAD ID
    if "norad_id" in data:
        if not validate_norad_id(data["norad_id"]):
            errors.append("Invalid NORAD ID")
    
    # Validate position data if present
    if "current_position" in data and data["current_position"]:
        pos = data["current_position"]
        if "latitude" in pos and "longitude" in pos:
            is_valid, error_msg = validate_coordinates(
                pos["latitude"], pos["longitude"]
            )
            if not is_valid:
                errors.append(f"Invalid position coordinates: {error_msg}")
    
    return len(errors) == 0, errors