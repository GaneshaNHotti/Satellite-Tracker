"""
Pass prediction service for satellite pass forecasting and management.
Provides enhanced pass predictions with filtering, sorting, caching, and alert preparation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import Depends

from app.database import get_db
from app.services.satellite_service import SatelliteService
from app.services.cache_service import CacheService
from app.models.cache import SatellitePassCache
from app.models.favorite import UserFavoriteSatellite
from app.models.user import User
from app.utils.exceptions import ValidationError, NotFoundError, ExternalAPIError
from app.utils.satellite_utils import validate_norad_id, validate_coordinates
from app.config import settings

logger = logging.getLogger(__name__)


class PassPredictionService:
    """
    Enhanced pass prediction service for satellite pass forecasting.
    Provides filtering, sorting, caching optimization, and alert preparation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.satellite_service = SatelliteService(db)
        self.cache_service = CacheService(db)
    
    async def get_satellite_passes(self, norad_id: int, latitude: float, longitude: float,
                                 altitude: float = 0, days: int = 10, min_elevation: float = 0,
                                 visibility_filter: str = "all", use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get satellite pass predictions with enhanced filtering and sorting.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            days: Number of days to predict (1-10)
            min_elevation: Minimum elevation for passes
            visibility_filter: Filter by visibility ("all", "visible", "bright")
            use_cache: Whether to use cached data
            
        Returns:
            List of enhanced pass prediction dictionaries
            
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
        
        if not (1 <= days <= 10):
            raise ValidationError("Days must be between 1 and 10", field="days")
        
        if not (0 <= min_elevation <= 90):
            raise ValidationError("Minimum elevation must be between 0 and 90 degrees", field="min_elevation")
        
        # Get pass predictions from satellite service
        passes_data = await self.satellite_service.get_satellite_passes(
            norad_id, latitude, longitude, altitude, days, min_elevation, use_cache
        )
        
        # Enhance pass data with additional information
        enhanced_passes = []
        for pass_data in passes_data:
            enhanced_pass = self._enhance_pass_data(pass_data, latitude, longitude)
            enhanced_passes.append(enhanced_pass)
        
        # Apply visibility filtering
        filtered_passes = self._filter_passes_by_visibility(enhanced_passes, visibility_filter)
        
        # Sort passes by start time and elevation
        sorted_passes = self._sort_passes_by_priority(filtered_passes)
        
        logger.info(f"Retrieved {len(sorted_passes)} passes for satellite {norad_id} (filtered from {len(passes_data)})")
        return sorted_passes
    
    async def get_all_favorite_passes(self, user_id: int, days: int = 10, min_elevation: float = 10,
                                    visibility_filter: str = "visible", max_passes_per_satellite: int = 5) -> List[Dict[str, Any]]:
        """
        Get pass predictions for all user's favorite satellites.
        
        Args:
            user_id: ID of the user
            days: Number of days to predict
            min_elevation: Minimum elevation for passes
            visibility_filter: Filter by visibility
            max_passes_per_satellite: Maximum passes per satellite
            
        Returns:
            List of pass predictions for all favorites
            
        Raises:
            NotFoundError: If user not found or has no location
        """
        # Get user and validate
        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found", resource_type="user", resource_id=str(user_id))
        
        # Check if user has a location
        if not user.locations:
            raise ValidationError("User must set location before getting pass predictions", field="location")
        
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
        
        # Get passes for all favorites
        all_passes = []
        
        for favorite in favorites:
            try:
                satellite_passes = await self.get_satellite_passes(
                    favorite.norad_id, latitude, longitude, 0, days, min_elevation, visibility_filter
                )
                
                # Limit passes per satellite
                limited_passes = satellite_passes[:max_passes_per_satellite]
                
                # Add satellite information to each pass
                for pass_data in limited_passes:
                    pass_data["satellite"] = {
                        "norad_id": favorite.norad_id,
                        "name": favorite.satellite.name if favorite.satellite else f"Satellite {favorite.norad_id}",
                        "category": favorite.satellite.category if favorite.satellite else "Unknown",
                        "favorite_id": favorite.id
                    }
                    all_passes.append(pass_data)
                
            except Exception as e:
                logger.warning(f"Failed to get passes for satellite {favorite.norad_id}: {e}")
                continue
        
        # Sort all passes by start time
        all_passes.sort(key=lambda x: x.get("start_time", ""))
        
        logger.info(f"Retrieved {len(all_passes)} total passes for {len(favorites)} favorite satellites")
        return all_passes
    
    def get_upcoming_passes(self, user_id: int, hours: int = 24, min_elevation: float = 10) -> List[Dict[str, Any]]:
        """
        Get upcoming passes for user's favorites from cache (fast lookup).
        
        Args:
            user_id: ID of the user
            hours: Number of hours to look ahead
            min_elevation: Minimum elevation for passes
            
        Returns:
            List of upcoming pass predictions from cache
        """
        # Get user and location
        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user or not user.locations:
            return []
        
        location = user.locations[-1]
        latitude = float(location.latitude)
        longitude = float(location.longitude)
        
        # Get user's favorite NORAD IDs
        favorite_norad_ids = [fav.norad_id for fav in user.favorites]
        if not favorite_norad_ids:
            return []
        
        # Calculate time range
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        # Query cached passes
        cached_passes = self.db.query(SatellitePassCache).filter(
            and_(
                SatellitePassCache.norad_id.in_(favorite_norad_ids),
                SatellitePassCache.latitude == latitude,
                SatellitePassCache.longitude == longitude,
                SatellitePassCache.start_time >= now,
                SatellitePassCache.start_time <= end_time,
                SatellitePassCache.max_elevation >= min_elevation,
                SatellitePassCache.expires_at > now
            )
        ).order_by(SatellitePassCache.start_time).all()
        
        # Convert to enhanced format
        upcoming_passes = []
        for cached_pass in cached_passes:
            pass_data = cached_pass.to_dict()
            enhanced_pass = self._enhance_pass_data(pass_data, latitude, longitude)
            
            # Add satellite information
            satellite = self.db.query(UserFavoriteSatellite).filter(
                and_(
                    UserFavoriteSatellite.user_id == user_id,
                    UserFavoriteSatellite.norad_id == cached_pass.norad_id
                )
            ).first()
            
            if satellite:
                enhanced_pass["satellite"] = {
                    "norad_id": satellite.norad_id,
                    "name": satellite.satellite.name if satellite.satellite else f"Satellite {satellite.norad_id}",
                    "category": satellite.satellite.category if satellite.satellite else "Unknown",
                    "favorite_id": satellite.id
                }
                upcoming_passes.append(enhanced_pass)
        
        logger.info(f"Retrieved {len(upcoming_passes)} upcoming passes from cache")
        return upcoming_passes
    
    def get_pass_alerts(self, user_id: int, alert_minutes: List[int] = [60, 15, 5]) -> List[Dict[str, Any]]:
        """
        Get passes that should trigger alerts based on timing.
        
        Args:
            user_id: ID of the user
            alert_minutes: List of minutes before pass to trigger alerts
            
        Returns:
            List of passes requiring alerts with alert timing information
        """
        alerts = []
        now = datetime.utcnow()
        
        for minutes in alert_minutes:
            alert_time = now + timedelta(minutes=minutes)
            alert_window_start = alert_time - timedelta(minutes=1)  # 1-minute window
            alert_window_end = alert_time + timedelta(minutes=1)
            
            # Get passes starting in the alert window
            passes_for_alert = self.get_upcoming_passes(user_id, hours=24)
            
            for pass_data in passes_for_alert:
                pass_start = datetime.fromisoformat(pass_data["start_time"].replace("Z", "+00:00"))
                
                if alert_window_start <= pass_start <= alert_window_end:
                    alert_info = {
                        "pass": pass_data,
                        "alert_type": f"{minutes}_minute_warning",
                        "alert_time": alert_time.isoformat(),
                        "pass_start_time": pass_start.isoformat(),
                        "minutes_until_pass": minutes
                    }
                    alerts.append(alert_info)
        
        logger.info(f"Generated {len(alerts)} pass alerts for user {user_id}")
        return alerts
    
    def optimize_pass_cache(self, location_radius_km: float = 50) -> Dict[str, int]:
        """
        Optimize pass cache by pre-computing passes for popular locations.
        
        Args:
            location_radius_km: Radius around user locations to consider
            
        Returns:
            Dictionary with optimization statistics
        """
        # Get all user locations
        users_with_locations = self.db.query(User).filter(User.locations.any()).all()
        
        if not users_with_locations:
            return {"locations_processed": 0, "passes_cached": 0}
        
        # Group nearby locations (simplified - could use proper clustering)
        unique_locations = []
        for user in users_with_locations:
            if user.locations:
                location = user.locations[-1]
                lat, lon = float(location.latitude), float(location.longitude)
                
                # Check if this location is close to any existing location
                is_duplicate = False
                for existing_lat, existing_lon in unique_locations:
                    # Simple distance check (could be improved)
                    if abs(lat - existing_lat) < 0.5 and abs(lon - existing_lon) < 0.5:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_locations.append((lat, lon))
        
        # Get all favorite satellites
        favorite_norad_ids = self.db.query(UserFavoriteSatellite.norad_id).distinct().all()
        norad_ids = [fav.norad_id for fav in favorite_norad_ids]
        
        passes_cached = 0
        
        # Pre-cache passes for each unique location and satellite combination
        for lat, lon in unique_locations:
            for norad_id in norad_ids[:10]:  # Limit to top 10 satellites to avoid overload
                try:
                    # Check if we already have recent cache
                    existing_cache = self.db.query(SatellitePassCache).filter(
                        and_(
                            SatellitePassCache.norad_id == norad_id,
                            SatellitePassCache.latitude == lat,
                            SatellitePassCache.longitude == lon,
                            SatellitePassCache.expires_at > datetime.utcnow()
                        )
                    ).first()
                    
                    if not existing_cache:
                        # Cache passes for this location/satellite
                        passes = self.satellite_service.get_satellite_passes(
                            norad_id, lat, lon, 0, 7, 0, use_cache=False
                        )
                        passes_cached += len(passes)
                
                except Exception as e:
                    logger.warning(f"Failed to cache passes for satellite {norad_id} at ({lat}, {lon}): {e}")
                    continue
        
        logger.info(f"Cache optimization completed: {len(unique_locations)} locations, {passes_cached} passes cached")
        return {"locations_processed": len(unique_locations), "passes_cached": passes_cached}
    
    def _enhance_pass_data(self, pass_data: Dict[str, Any], observer_lat: float, observer_lon: float) -> Dict[str, Any]:
        """
        Enhance pass data with additional calculations and information.
        
        Args:
            pass_data: Raw pass data
            observer_lat: Observer latitude
            observer_lon: Observer longitude
            
        Returns:
            Enhanced pass data dictionary
        """
        enhanced = pass_data.copy()
        
        # Add observer information
        enhanced["observer"] = {
            "latitude": observer_lat,
            "longitude": observer_lon
        }
        
        # Calculate pass characteristics
        if "start_time" in enhanced and "end_time" in enhanced:
            try:
                start_time = datetime.fromisoformat(enhanced["start_time"].replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(enhanced["end_time"].replace("Z", "+00:00"))
                
                duration = (end_time - start_time).total_seconds()
                enhanced["duration_seconds"] = int(duration)
                enhanced["duration_formatted"] = self._format_duration(duration)
                
                # Time until pass
                now = datetime.utcnow().replace(tzinfo=start_time.tzinfo)
                if start_time > now:
                    time_until = (start_time - now).total_seconds()
                    enhanced["time_until_seconds"] = int(time_until)
                    enhanced["time_until_formatted"] = self._format_duration(time_until)
                else:
                    enhanced["time_until_seconds"] = 0
                    enhanced["time_until_formatted"] = "Pass has started"
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating pass timing: {e}")
        
        # Determine visibility quality
        enhanced["visibility_quality"] = self._determine_visibility_quality(enhanced)
        
        # Add pass priority score for sorting
        enhanced["priority_score"] = self._calculate_pass_priority(enhanced)
        
        # Add formatted elevation information
        max_elevation = enhanced.get("max_elevation", 0)
        enhanced["elevation_category"] = self._categorize_elevation(max_elevation)
        
        return enhanced
    
    def _filter_passes_by_visibility(self, passes: List[Dict[str, Any]], visibility_filter: str) -> List[Dict[str, Any]]:
        """
        Filter passes based on visibility criteria.
        
        Args:
            passes: List of pass data dictionaries
            visibility_filter: Filter type ("all", "visible", "bright")
            
        Returns:
            Filtered list of passes
        """
        if visibility_filter == "all":
            return passes
        
        filtered = []
        
        for pass_data in passes:
            visibility_quality = pass_data.get("visibility_quality", {})
            
            if visibility_filter == "visible":
                # Include passes that are visible (elevation > 10° or magnitude < 4)
                if (pass_data.get("max_elevation", 0) > 10 or 
                    (pass_data.get("magnitude") is not None and pass_data.get("magnitude") < 4)):
                    filtered.append(pass_data)
            
            elif visibility_filter == "bright":
                # Include only bright passes (magnitude < 2 or elevation > 30°)
                if (pass_data.get("magnitude") is not None and pass_data.get("magnitude") < 2) or \
                   pass_data.get("max_elevation", 0) > 30:
                    filtered.append(pass_data)
        
        return filtered
    
    def _sort_passes_by_priority(self, passes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort passes by priority (time, elevation, brightness).
        
        Args:
            passes: List of pass data dictionaries
            
        Returns:
            Sorted list of passes
        """
        def sort_key(pass_data):
            # Primary: start time (earlier passes first)
            start_time = pass_data.get("start_time", "9999-12-31T23:59:59Z")
            
            # Secondary: priority score (higher is better)
            priority_score = pass_data.get("priority_score", 0)
            
            return (start_time, -priority_score)
        
        return sorted(passes, key=sort_key)
    
    def _determine_visibility_quality(self, pass_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the visibility quality of a pass.
        
        Args:
            pass_data: Pass data dictionary
            
        Returns:
            Visibility quality information
        """
        max_elevation = pass_data.get("max_elevation", 0)
        magnitude = pass_data.get("magnitude")
        
        quality = {
            "rating": "poor",
            "score": 0,
            "factors": []
        }
        
        # Elevation factor
        if max_elevation > 60:
            quality["rating"] = "excellent"
            quality["score"] += 40
            quality["factors"].append("Very high elevation")
        elif max_elevation > 30:
            quality["rating"] = "good"
            quality["score"] += 25
            quality["factors"].append("High elevation")
        elif max_elevation > 10:
            quality["rating"] = "fair"
            quality["score"] += 10
            quality["factors"].append("Moderate elevation")
        
        # Brightness factor
        if magnitude is not None:
            if magnitude < -2:
                quality["score"] += 30
                quality["factors"].append("Very bright")
            elif magnitude < 0:
                quality["score"] += 20
                quality["factors"].append("Bright")
            elif magnitude < 2:
                quality["score"] += 10
                quality["factors"].append("Moderately bright")
        
        # Duration factor
        duration = pass_data.get("duration_seconds", 0)
        if duration > 600:  # > 10 minutes
            quality["score"] += 15
            quality["factors"].append("Long duration")
        elif duration > 300:  # > 5 minutes
            quality["score"] += 10
            quality["factors"].append("Good duration")
        
        # Update rating based on total score
        if quality["score"] >= 50:
            quality["rating"] = "excellent"
        elif quality["score"] >= 30:
            quality["rating"] = "good"
        elif quality["score"] >= 15:
            quality["rating"] = "fair"
        
        return quality
    
    def _calculate_pass_priority(self, pass_data: Dict[str, Any]) -> int:
        """
        Calculate a priority score for pass sorting.
        
        Args:
            pass_data: Pass data dictionary
            
        Returns:
            Priority score (higher is better)
        """
        score = 0
        
        # Elevation score (0-40 points)
        max_elevation = pass_data.get("max_elevation", 0)
        score += min(40, max_elevation * 0.67)  # Max 40 points for 60° elevation
        
        # Brightness score (0-30 points)
        magnitude = pass_data.get("magnitude")
        if magnitude is not None:
            # Lower magnitude = brighter = higher score
            brightness_score = max(0, 30 - (magnitude * 5))
            score += min(30, brightness_score)
        
        # Duration score (0-20 points)
        duration = pass_data.get("duration_seconds", 0)
        duration_score = min(20, duration / 30)  # Max 20 points for 10+ minute passes
        score += duration_score
        
        # Time preference (0-10 points) - prefer passes in next 24 hours
        time_until = pass_data.get("time_until_seconds", float('inf'))
        if time_until < 86400:  # Within 24 hours
            time_score = 10 - (time_until / 8640)  # Decreasing score over 24 hours
            score += max(0, time_score)
        
        return int(score)
    
    def _categorize_elevation(self, elevation: float) -> str:
        """
        Categorize elevation for user-friendly display.
        
        Args:
            elevation: Maximum elevation in degrees
            
        Returns:
            Elevation category string
        """
        if elevation >= 60:
            return "overhead"
        elif elevation >= 30:
            return "high"
        elif elevation >= 10:
            return "medium"
        else:
            return "low"
    
    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to human-readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


# Dependency function for FastAPI
def get_pass_prediction_service(db: Session = Depends(get_db)) -> PassPredictionService:
    """Dependency function to get pass prediction service instance."""
    return PassPredictionService(db)