"""
Position tracking service for real-time satellite position management.
Provides enhanced position tracking with history, automatic refresh, and coordinate conversion.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from fastapi import Depends

from app.database import get_db
from app.services.satellite_service import SatelliteService
from app.services.cache_service import CacheService
from app.models.cache import SatellitePositionCache
from app.models.favorite import UserFavoriteSatellite
from app.models.user import User
from app.utils.exceptions import ValidationError, NotFoundError, ExternalAPIError
from app.utils.satellite_utils import validate_norad_id, validate_coordinates
from app.config import settings

logger = logging.getLogger(__name__)


class PositionTrackingService:
    """
    Enhanced position tracking service for real-time satellite monitoring.
    Provides position history, automatic refresh, and coordinate conversion utilities.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.satellite_service = SatelliteService(db)
        self.cache_service = CacheService(db)
    
    async def get_real_time_position(self, norad_id: int, latitude: float, longitude: float,
                                   altitude: float = 0, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get real-time satellite position with enhanced data formatting.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            force_refresh: Force fresh data from API
            
        Returns:
            Enhanced position data with additional calculations
            
        Raises:
            ValidationError: If parameters are invalid
            ExternalAPIError: If API request fails
        """
        # Validate inputs
        if not validate_norad_id(norad_id):
            raise ValidationError(f"Invalid NORAD ID: {norad_id}", field="norad_id")
        
        is_valid, error_msg = validate_coordinates(latitude, longitude)
        if not is_valid:
            raise ValidationError(error_msg, field="coordinates")
        
        # Get position data (force refresh if requested)
        use_cache = not force_refresh
        position_data = await self.satellite_service.get_satellite_position(
            norad_id, latitude, longitude, altitude, use_cache=use_cache
        )
        
        # Enhance position data with additional calculations
        enhanced_position = self._enhance_position_data(position_data, latitude, longitude, altitude)
        
        logger.info(f"Retrieved real-time position for satellite {norad_id}")
        return enhanced_position
    
    async def get_multiple_positions(self, norad_ids: List[int], latitude: float, longitude: float,
                                   altitude: float = 0, max_concurrent: int = 5) -> Dict[int, Dict[str, Any]]:
        """
        Get positions for multiple satellites efficiently with concurrency control.
        
        Args:
            norad_ids: List of NORAD IDs
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            max_concurrent: Maximum concurrent API requests
            
        Returns:
            Dictionary mapping NORAD ID to position data
        """
        # Validate coordinates once
        is_valid, error_msg = validate_coordinates(latitude, longitude)
        if not is_valid:
            raise ValidationError(error_msg, field="coordinates")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_single_position(norad_id: int) -> Tuple[int, Optional[Dict[str, Any]]]:
            async with semaphore:
                try:
                    position = await self.get_real_time_position(norad_id, latitude, longitude, altitude)
                    return norad_id, position
                except Exception as e:
                    logger.warning(f"Failed to get position for satellite {norad_id}: {e}")
                    return norad_id, None
        
        # Execute requests concurrently
        tasks = [get_single_position(norad_id) for norad_id in norad_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        positions = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception in position retrieval: {result}")
                continue
            
            norad_id, position_data = result
            if position_data:
                positions[norad_id] = position_data
        
        logger.info(f"Retrieved positions for {len(positions)}/{len(norad_ids)} satellites")
        return positions
    
    async def get_favorite_positions(self, user_id: int, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get current positions for all user's favorite satellites.
        
        Args:
            user_id: ID of the user
            force_refresh: Force fresh data from API
            
        Returns:
            List of favorite satellites with current positions
            
        Raises:
            NotFoundError: If user not found or has no location
        """
        # Get user and validate
        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found", resource_type="user", resource_id=str(user_id))
        
        # Check if user has a location
        if not user.locations:
            raise ValidationError("User must set location before getting satellite positions", field="location")
        
        # Use the most recent location
        location = user.locations[-1]
        latitude = float(location.latitude)
        longitude = float(location.longitude)
        
        # Get user's favorite satellites
        favorites = self.db.query(UserFavoriteSatellite).filter(
            UserFavoriteSatellite.user_id == user_id
        ).all()
        
        if not favorites:
            return []
        
        # Get NORAD IDs
        norad_ids = [fav.norad_id for fav in favorites]
        
        # Get positions for all favorites
        positions = await self.get_multiple_positions(norad_ids, latitude, longitude)
        
        # Combine with favorite information
        result = []
        for favorite in favorites:
            satellite_info = {
                "favorite_id": favorite.id,
                "norad_id": favorite.norad_id,
                "name": favorite.satellite.name if favorite.satellite else f"Satellite {favorite.norad_id}",
                "category": favorite.satellite.category if favorite.satellite else "Unknown",
                "added_at": favorite.created_at,
                "current_position": positions.get(favorite.norad_id)
            }
            result.append(satellite_info)
        
        logger.info(f"Retrieved positions for {len([r for r in result if r['current_position']])}/{len(result)} favorite satellites")
        return result
    
    def get_position_history(self, norad_id: int, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get position history for a satellite from cache.
        
        Args:
            norad_id: NORAD ID of the satellite
            hours: Number of hours of history to retrieve
            limit: Maximum number of position records
            
        Returns:
            List of historical position data
            
        Raises:
            ValidationError: If NORAD ID is invalid
        """
        if not validate_norad_id(norad_id):
            raise ValidationError(f"Invalid NORAD ID: {norad_id}", field="norad_id")
        
        # Calculate time range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query position history
        positions = self.db.query(SatellitePositionCache).filter(
            and_(
                SatellitePositionCache.norad_id == norad_id,
                SatellitePositionCache.created_at >= cutoff_time
            )
        ).order_by(desc(SatellitePositionCache.created_at)).limit(limit).all()
        
        # Convert to dictionaries and enhance
        history = []
        for position in positions:
            position_data = position.to_dict()
            # Add time since last update
            if position.created_at:
                time_diff = datetime.utcnow() - position.created_at
                position_data["age_seconds"] = int(time_diff.total_seconds())
            
            history.append(position_data)
        
        logger.info(f"Retrieved {len(history)} position records for satellite {norad_id}")
        return history
    
    async def refresh_stale_positions(self, max_age_minutes: int = 5, batch_size: int = 10) -> Dict[str, int]:
        """
        Automatically refresh stale position data for active satellites.
        
        Args:
            max_age_minutes: Maximum age before position is considered stale
            batch_size: Number of satellites to refresh in one batch
            
        Returns:
            Dictionary with refresh statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # Find satellites with stale position data that are in someone's favorites
        stale_satellites = self.db.query(SatellitePositionCache.norad_id).filter(
            SatellitePositionCache.created_at < cutoff_time
        ).distinct().limit(batch_size).all()
        
        if not stale_satellites:
            return {"refreshed": 0, "failed": 0, "total": 0}
        
        norad_ids = [sat.norad_id for sat in stale_satellites]
        
        # Get a representative location (could be improved to use multiple locations)
        # For now, use a default location or the first user's location
        default_lat, default_lon = 40.7128, -74.0060  # New York as default
        
        # Try to get a real user location
        user_with_location = self.db.query(User).filter(User.locations.any()).first()
        if user_with_location and user_with_location.locations:
            location = user_with_location.locations[-1]
            default_lat = float(location.latitude)
            default_lon = float(location.longitude)
        
        # Refresh positions
        refreshed = 0
        failed = 0
        
        for norad_id in norad_ids:
            try:
                await self.get_real_time_position(norad_id, default_lat, default_lon, force_refresh=True)
                refreshed += 1
            except Exception as e:
                logger.warning(f"Failed to refresh position for satellite {norad_id}: {e}")
                failed += 1
        
        logger.info(f"Position refresh completed: {refreshed} refreshed, {failed} failed")
        return {"refreshed": refreshed, "failed": failed, "total": len(norad_ids)}
    
    def _enhance_position_data(self, position_data: Dict[str, Any], observer_lat: float, 
                             observer_lon: float, observer_alt: float = 0) -> Dict[str, Any]:
        """
        Enhance position data with additional calculations and formatting.
        
        Args:
            position_data: Raw position data from N2YO API
            observer_lat: Observer latitude
            observer_lon: Observer longitude
            observer_alt: Observer altitude in meters
            
        Returns:
            Enhanced position data dictionary
        """
        enhanced = position_data.copy()
        
        # Add observer information
        enhanced["observer"] = {
            "latitude": observer_lat,
            "longitude": observer_lon,
            "altitude": observer_alt
        }
        
        # Add coordinate conversions and calculations
        sat_lat = position_data.get("satlatitude", 0)
        sat_lon = position_data.get("satlongitude", 0)
        sat_alt = position_data.get("sataltitude", 0)
        
        # Calculate distance from observer to satellite
        if sat_lat and sat_lon and sat_alt:
            distance = self._calculate_distance(observer_lat, observer_lon, observer_alt, 
                                              sat_lat, sat_lon, sat_alt)
            enhanced["distance_km"] = round(distance, 2)
        
        # Add visibility information
        enhanced["visibility"] = self._determine_visibility(position_data)
        
        # Add timestamp information
        enhanced["retrieved_at"] = datetime.utcnow().isoformat()
        
        # Format coordinates for better readability
        if "satlatitude" in enhanced:
            enhanced["formatted_coordinates"] = {
                "latitude": f"{enhanced['satlatitude']:.6f}°",
                "longitude": f"{enhanced['satlongitude']:.6f}°",
                "altitude": f"{enhanced.get('sataltitude', 0):.2f} km"
            }
        
        return enhanced
    
    def _calculate_distance(self, lat1: float, lon1: float, alt1: float,
                          lat2: float, lon2: float, alt2: float) -> float:
        """
        Calculate distance between observer and satellite using 3D coordinates.
        
        Args:
            lat1, lon1, alt1: Observer coordinates (altitude in meters)
            lat2, lon2, alt2: Satellite coordinates (altitude in kilometers)
            
        Returns:
            Distance in kilometers
        """
        import math
        
        # Earth radius in kilometers
        R = 6371.0
        
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Convert observer altitude to kilometers
        alt1_km = alt1 / 1000.0
        
        # Calculate 3D coordinates
        x1 = (R + alt1_km) * math.cos(lat1_rad) * math.cos(lon1_rad)
        y1 = (R + alt1_km) * math.cos(lat1_rad) * math.sin(lon1_rad)
        z1 = (R + alt1_km) * math.sin(lat1_rad)
        
        x2 = (R + alt2) * math.cos(lat2_rad) * math.cos(lon2_rad)
        y2 = (R + alt2) * math.cos(lat2_rad) * math.sin(lon2_rad)
        z2 = (R + alt2) * math.sin(lat2_rad)
        
        # Calculate 3D distance
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
        
        return distance
    
    def _determine_visibility(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine satellite visibility based on position data.
        
        Args:
            position_data: Position data from N2YO API
            
        Returns:
            Visibility information dictionary
        """
        visibility_info = {
            "is_visible": False,
            "status": "unknown",
            "reason": ""
        }
        
        # Check if satellite is above horizon (basic check)
        elevation = position_data.get("elevation", 0)
        if elevation is not None:
            if elevation > 0:
                visibility_info["is_visible"] = True
                visibility_info["status"] = "above_horizon"
                visibility_info["reason"] = f"Satellite is {elevation:.1f}° above horizon"
            else:
                visibility_info["status"] = "below_horizon"
                visibility_info["reason"] = f"Satellite is {abs(elevation):.1f}° below horizon"
        
        # Add sun angle information if available
        if "eclipsed" in position_data:
            if position_data["eclipsed"]:
                visibility_info["is_visible"] = False
                visibility_info["status"] = "eclipsed"
                visibility_info["reason"] = "Satellite is in Earth's shadow"
        
        return visibility_info


# Dependency function for FastAPI
def get_position_tracking_service(db: Session = Depends(get_db)) -> PositionTrackingService:
    """Dependency function to get position tracking service instance."""
    return PositionTrackingService(db)