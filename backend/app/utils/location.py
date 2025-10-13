"""
Location-related utility functions for coordinate validation and calculations.
"""

import math
from decimal import Decimal
from typing import Tuple, Optional


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Args:
        latitude: Latitude coordinate (-90 to 90)
        longitude: Longitude coordinate (-180 to 180)
    
    Returns:
        bool: True if coordinates are valid, False otherwise
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False


def normalize_longitude(longitude: float) -> float:
    """
    Normalize longitude to be within -180 to 180 range.
    
    Args:
        longitude: Longitude coordinate
    
    Returns:
        float: Normalized longitude
    """
    lon = float(longitude)
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth using Haversine formula.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
    
    Returns:
        float: Distance in kilometers
    """
    # Convert latitude and longitude from degrees to radians
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
    
    # Radius of Earth in kilometers
    earth_radius_km = 6371.0
    
    return earth_radius_km * c


def format_coordinates(latitude: float, longitude: float, precision: int = 6) -> Tuple[str, str]:
    """
    Format coordinates to specified decimal precision with directional indicators.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        precision: Number of decimal places (default: 6)
    
    Returns:
        Tuple[str, str]: Formatted (latitude, longitude) strings
    """
    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"
    
    lat_str = f"{abs(latitude):.{precision}f}°{lat_dir}"
    lon_str = f"{abs(longitude):.{precision}f}°{lon_dir}"
    
    return lat_str, lon_str


def parse_coordinate_string(coord_str: str) -> Optional[float]:
    """
    Parse a coordinate string that may include directional indicators.
    
    Args:
        coord_str: Coordinate string (e.g., "40.7128°N", "-74.0060", "74.0060°W")
    
    Returns:
        Optional[float]: Parsed coordinate or None if invalid
    """
    if not coord_str:
        return None
    
    try:
        # Remove whitespace and convert to uppercase
        coord_str = coord_str.strip().upper()
        
        # Check for directional indicators
        is_negative = False
        if coord_str.endswith(('S', 'W')):
            is_negative = True
            coord_str = coord_str[:-1]
        elif coord_str.endswith(('N', 'E')):
            coord_str = coord_str[:-1]
        
        # Remove degree symbol if present
        coord_str = coord_str.replace('°', '')
        
        # Parse the numeric value
        value = float(coord_str)
        
        # Apply negative sign if needed
        if is_negative:
            value = -value
        
        return value
    
    except (ValueError, TypeError):
        return None


def is_valid_latitude(latitude: float) -> bool:
    """
    Check if a latitude value is valid.
    
    Args:
        latitude: Latitude coordinate
    
    Returns:
        bool: True if valid latitude, False otherwise
    """
    try:
        lat = float(latitude)
        return -90 <= lat <= 90
    except (ValueError, TypeError):
        return False


def is_valid_longitude(longitude: float) -> bool:
    """
    Check if a longitude value is valid.
    
    Args:
        longitude: Longitude coordinate
    
    Returns:
        bool: True if valid longitude, False otherwise
    """
    try:
        lon = float(longitude)
        return -180 <= lon <= 180
    except (ValueError, TypeError):
        return False


def decimal_to_dms(decimal_degrees: float) -> Tuple[int, int, float]:
    """
    Convert decimal degrees to degrees, minutes, seconds format.
    
    Args:
        decimal_degrees: Coordinate in decimal degrees
    
    Returns:
        Tuple[int, int, float]: (degrees, minutes, seconds)
    """
    abs_degrees = abs(decimal_degrees)
    degrees = int(abs_degrees)
    minutes_float = (abs_degrees - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    
    return degrees, minutes, seconds


def dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str = 'N') -> float:
    """
    Convert degrees, minutes, seconds to decimal degrees.
    
    Args:
        degrees: Degrees component
        minutes: Minutes component
        seconds: Seconds component
        direction: Direction ('N', 'S', 'E', 'W')
    
    Returns:
        float: Coordinate in decimal degrees
    """
    decimal = degrees + minutes / 60 + seconds / 3600
    
    if direction.upper() in ['S', 'W']:
        decimal = -decimal
    
    return decimal