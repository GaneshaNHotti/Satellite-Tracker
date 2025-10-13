"""
Satellite service that integrates N2YO API with caching layer.
Provides high-level satellite data operations with automatic caching and fallback logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.services.n2yo_service import N2YOService
from app.services.cache_service import CacheService
from app.models.satellite import Satellite
from app.utils.exceptions import ExternalAPIError, NotFoundError, ValidationError
from app.utils.satellite_utils import (
    validate_norad_id, 
    validate_coordinates, 
    format_satellite_name,
    categorize_satellite,
    filter_passes_by_visibility,
    sort_passes_by_time
)

logger = logging.getLogger(__name__)


class SatelliteService:
    """
    High-level satellite service that combines N2YO API with caching.
    Provides automatic caching, fallback logic, and data validation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_service = CacheService(db)
        self.n2yo_service = N2YOService()
    
    async def search_satellites(self, query: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Search for satellites by name with caching support.
        
        Args:
            query: Search query (satellite name)
            use_cache: Whether to use cached results
            
        Returns:
            List of satellite information dictionaries
            
        Raises:
            ValidationError: If query is invalid
            ExternalAPIError: If API request fails
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError("Search query must be at least 2 characters long", field="query")
        
        query = query.strip()
        
        try:
            # For search operations, we'll always hit the API since results can change
            # and search queries are too varied to cache effectively
            async with self.n2yo_service as n2yo:
                satellites = await n2yo.search_satellites(query)
            
            # Process and enhance satellite data
            enhanced_satellites = []
            for sat_data in satellites:
                # Format and categorize satellite
                sat_data["name"] = format_satellite_name(sat_data.get("name", ""))
                if not sat_data.get("category"):
                    sat_data["category"] = categorize_satellite(sat_data["name"])
                
                # Store/update satellite in database for future reference
                await self._store_satellite_info(sat_data)
                
                enhanced_satellites.append(sat_data)
            
            logger.info(f"Search for '{query}' returned {len(enhanced_satellites)} satellites")
            return enhanced_satellites
            
        except ExternalAPIError:
            # If API fails, try to find satellites in local database
            logger.warning(f"N2YO API failed for search '{query}', falling back to local database")
            return self._search_local_satellites(query)
    
    async def get_satellite_info(self, norad_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed satellite information with caching.
        
        Args:
            norad_id: NORAD ID of the satellite
            use_cache: Whether to use cached data
            
        Returns:
            Satellite information dictionary
            
        Raises:
            ValidationError: If NORAD ID is invalid
            NotFoundError: If satellite is not found
            ExternalAPIError: If API request fails and no cached data available
        """
        if not validate_norad_id(norad_id):
            raise ValidationError(f"Invalid NORAD ID: {norad_id}", field="norad_id")
        
        # Check local database first
        satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
        
        try:
            # Try to get fresh data from API
            async with self.n2yo_service as n2yo:
                api_data = await n2yo.get_satellite_info(norad_id)
            
            # Enhance and store the data
            api_data["name"] = format_satellite_name(api_data.get("name", ""))
            if not api_data.get("category"):
                api_data["category"] = categorize_satellite(api_data["name"])
            
            await self._store_satellite_info(api_data)
            
            logger.info(f"Retrieved satellite info for {norad_id} from API")
            return api_data
            
        except ExternalAPIError as e:
            # If API fails, use local database as fallback
            if satellite:
                logger.warning(f"N2YO API failed for satellite {norad_id}, using cached data: {e}")
                return satellite.to_dict()
            else:
                logger.error(f"N2YO API failed and no local data for satellite {norad_id}: {e}")
                raise NotFoundError(f"Satellite {norad_id} not found", resource_type="satellite", resource_id=str(norad_id))
    
    async def get_satellite_position(self, norad_id: int, latitude: float, longitude: float, 
                                   altitude: float = 0, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get current satellite position with caching.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            use_cache: Whether to use cached data
            
        Returns:
            Satellite position data dictionary
            
        Raises:
            ValidationError: If parameters are invalid
            ExternalAPIError: If API request fails and no cached data available
        """
        # Validate inputs
        if not validate_norad_id(norad_id):
            raise ValidationError(f"Invalid NORAD ID: {norad_id}", field="norad_id")
        
        is_valid, error_msg = validate_coordinates(latitude, longitude)
        if not is_valid:
            raise ValidationError(error_msg, field="coordinates")
        
        # Check cache first if enabled
        if use_cache:
            cached_position = self.cache_service.get_cached_position(norad_id)
            if cached_position:
                logger.debug(f"Using cached position for satellite {norad_id}")
                return cached_position
        
        try:
            # Get fresh data from API
            async with self.n2yo_service as n2yo:
                position_data = await n2yo.get_satellite_position(norad_id, latitude, longitude, altitude)
            
            # Cache the position data
            self.cache_service.cache_position(norad_id, position_data)
            
            logger.info(f"Retrieved position for satellite {norad_id} from API")
            return position_data
            
        except ExternalAPIError as e:
            # If API fails and cache is disabled or empty, try to get any cached data
            if not use_cache:
                cached_position = self.cache_service.get_cached_position(norad_id)
                if cached_position:
                    logger.warning(f"N2YO API failed for position {norad_id}, using stale cached data: {e}")
                    return cached_position
            
            logger.error(f"N2YO API failed and no cached position for satellite {norad_id}: {e}")
            raise ExternalAPIError(f"Unable to get position for satellite {norad_id}: {e}", api_name="N2YO")
    
    async def get_satellite_passes(self, norad_id: int, latitude: float, longitude: float,
                                 altitude: float = 0, days: int = 10, min_elevation: float = 0,
                                 use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get satellite pass predictions with caching and filtering.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            days: Number of days to predict (1-10)
            min_elevation: Minimum elevation for visible passes
            use_cache: Whether to use cached data
            
        Returns:
            List of pass prediction dictionaries
            
        Raises:
            ValidationError: If parameters are invalid
            ExternalAPIError: If API request fails and no cached data available
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
        
        # Check cache first if enabled
        if use_cache:
            cached_passes = self.cache_service.get_cached_passes(norad_id, latitude, longitude)
            if cached_passes:
                # Filter and sort cached passes
                filtered_passes = filter_passes_by_visibility(cached_passes, min_elevation)
                sorted_passes = sort_passes_by_time(filtered_passes)
                logger.debug(f"Using cached passes for satellite {norad_id}")
                return sorted_passes
        
        try:
            # Get fresh data from API
            async with self.n2yo_service as n2yo:
                passes_data = await n2yo.get_satellite_passes(norad_id, latitude, longitude, altitude, days)
            
            # Cache the passes data
            self.cache_service.cache_passes(norad_id, latitude, longitude, passes_data)
            
            # Filter and sort passes
            filtered_passes = filter_passes_by_visibility(passes_data, min_elevation)
            sorted_passes = sort_passes_by_time(filtered_passes)
            
            logger.info(f"Retrieved {len(sorted_passes)} passes for satellite {norad_id} from API")
            return sorted_passes
            
        except ExternalAPIError as e:
            # If API fails and cache is disabled or empty, try to get any cached data
            if not use_cache:
                cached_passes = self.cache_service.get_cached_passes(norad_id, latitude, longitude)
                if cached_passes:
                    filtered_passes = filter_passes_by_visibility(cached_passes, min_elevation)
                    sorted_passes = sort_passes_by_time(filtered_passes)
                    logger.warning(f"N2YO API failed for passes {norad_id}, using stale cached data: {e}")
                    return sorted_passes
            
            logger.error(f"N2YO API failed and no cached passes for satellite {norad_id}: {e}")
            raise ExternalAPIError(f"Unable to get passes for satellite {norad_id}: {e}", api_name="N2YO")
    
    async def get_multiple_satellite_positions(self, norad_ids: List[int], latitude: float, 
                                             longitude: float, altitude: float = 0,
                                             use_cache: bool = True) -> Dict[int, Dict[str, Any]]:
        """
        Get positions for multiple satellites efficiently.
        
        Args:
            norad_ids: List of NORAD IDs
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping NORAD ID to position data
        """
        positions = {}
        
        for norad_id in norad_ids:
            try:
                position = await self.get_satellite_position(norad_id, latitude, longitude, altitude, use_cache)
                positions[norad_id] = position
            except Exception as e:
                logger.warning(f"Failed to get position for satellite {norad_id}: {e}")
                # Continue with other satellites
                continue
        
        return positions
    
    def invalidate_satellite_cache(self, norad_id: int) -> bool:
        """
        Invalidate all cached data for a satellite.
        
        Args:
            norad_id: NORAD ID of the satellite
            
        Returns:
            True if successful, False otherwise
        """
        return self.cache_service.invalidate_satellite_cache(norad_id)
    
    def cleanup_expired_cache(self) -> Dict[str, int]:
        """
        Clean up expired cache entries.
        
        Returns:
            Dictionary with cleanup statistics
        """
        return self.cache_service.cleanup_all_expired()
    
    def get_api_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get N2YO API rate limit status.
        
        Returns:
            Rate limit information
        """
        return self.n2yo_service.get_rate_limit_status()
    
    # Private helper methods
    
    async def _store_satellite_info(self, satellite_data: Dict[str, Any]) -> Satellite:
        """
        Store or update satellite information in the database.
        
        Args:
            satellite_data: Satellite data dictionary
            
        Returns:
            Satellite model instance
        """
        norad_id = satellite_data["norad_id"]
        
        # Check if satellite already exists
        satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
        
        if satellite:
            # Update existing satellite
            satellite.name = satellite_data.get("name", satellite.name)
            satellite.launch_date = satellite_data.get("launch_date", satellite.launch_date)
            satellite.country = satellite_data.get("country", satellite.country)
            satellite.category = satellite_data.get("category", satellite.category)
            satellite.updated_at = datetime.utcnow()
        else:
            # Create new satellite
            satellite = Satellite(
                norad_id=norad_id,
                name=satellite_data.get("name", f"Satellite {norad_id}"),
                launch_date=satellite_data.get("launch_date"),
                country=satellite_data.get("country"),
                category=satellite_data.get("category", "Other")
            )
            self.db.add(satellite)
        
        try:
            self.db.commit()
            logger.debug(f"Stored satellite info for {norad_id}")
        except Exception as e:
            logger.error(f"Error storing satellite info for {norad_id}: {e}")
            self.db.rollback()
        
        return satellite
    
    def _search_local_satellites(self, query: str) -> List[Dict[str, Any]]:
        """
        Search satellites in local database as fallback.
        
        Args:
            query: Search query
            
        Returns:
            List of satellite dictionaries
        """
        try:
            satellites = self.db.query(Satellite).filter(
                Satellite.name.ilike(f"%{query}%")
            ).limit(50).all()
            
            result = [satellite.to_dict() for satellite in satellites]
            logger.info(f"Local search for '{query}' returned {len(result)} satellites")
            return result
            
        except Exception as e:
            logger.error(f"Error searching local satellites: {e}")
            return []


# Dependency function for FastAPI
def get_satellite_service(db: Session = Depends(get_db)) -> SatelliteService:
    """Dependency function to get satellite service instance."""
    return SatelliteService(db)