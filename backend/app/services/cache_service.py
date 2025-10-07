"""
Cache service for managing satellite position and pass prediction caching.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.cache import SatellitePositionCache, SatellitePassCache
from app.models.satellite import Satellite
from app.redis_client import cache
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing satellite data caching."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Satellite Position Caching
    
    def get_cached_position(self, norad_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached satellite position data.
        
        Args:
            norad_id: NORAD ID of the satellite
            
        Returns:
            Position data dictionary or None if not cached or expired
        """
        try:
            # First try Redis cache
            redis_key = f"satellite_position:{norad_id}"
            cached_data = cache.get(redis_key)
            if cached_data:
                logger.debug(f"Position cache hit (Redis) for satellite {norad_id}")
                return cached_data
            
            # Then try database cache
            position_cache = self.db.query(SatellitePositionCache).filter(
                SatellitePositionCache.norad_id == norad_id
            ).order_by(SatellitePositionCache.created_at.desc()).first()
            
            if position_cache and not position_cache.is_expired(settings.satellite_position_cache_ttl // 60):
                position_data = position_cache.to_dict()
                # Store in Redis for faster access
                cache.set(redis_key, position_data, ttl=settings.satellite_position_cache_ttl)
                logger.debug(f"Position cache hit (DB) for satellite {norad_id}")
                return position_data
            
            logger.debug(f"Position cache miss for satellite {norad_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached position for satellite {norad_id}: {e}")
            return None
    
    def cache_position(self, norad_id: int, position_data: Dict[str, Any]) -> bool:
        """
        Cache satellite position data.
        
        Args:
            norad_id: NORAD ID of the satellite
            position_data: Position data from N2YO API
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            # Ensure satellite exists in database
            satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
            if not satellite:
                logger.warning(f"Satellite {norad_id} not found in database, cannot cache position")
                return False
            
            # Create database cache entry
            position_cache = SatellitePositionCache.from_n2yo_data(norad_id, position_data)
            self.db.add(position_cache)
            self.db.commit()
            
            # Cache in Redis
            redis_key = f"satellite_position:{norad_id}"
            cache_data = position_cache.to_dict()
            cache.set(redis_key, cache_data, ttl=settings.satellite_position_cache_ttl)
            
            logger.debug(f"Position cached for satellite {norad_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching position for satellite {norad_id}: {e}")
            self.db.rollback()
            return False
    
    def cleanup_expired_positions(self) -> int:
        """
        Clean up expired position cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=settings.satellite_position_cache_ttl * 2)
            
            deleted_count = self.db.query(SatellitePositionCache).filter(
                SatellitePositionCache.created_at < cutoff_time
            ).delete()
            
            self.db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired position cache entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired position cache: {e}")
            self.db.rollback()
            return 0
    
    # Satellite Pass Caching
    
    def get_cached_passes(self, norad_id: int, latitude: float, longitude: float) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached satellite pass predictions.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            
        Returns:
            List of pass data dictionaries or None if not cached or expired
        """
        try:
            # Try Redis cache first
            redis_key = f"satellite_passes:{norad_id}:{latitude}:{longitude}"
            cached_data = cache.get(redis_key)
            if cached_data:
                logger.debug(f"Pass cache hit (Redis) for satellite {norad_id}")
                return cached_data
            
            # Then try database cache
            passes_cache = self.db.query(SatellitePassCache).filter(
                and_(
                    SatellitePassCache.norad_id == norad_id,
                    SatellitePassCache.latitude == latitude,
                    SatellitePassCache.longitude == longitude,
                    SatellitePassCache.expires_at > datetime.utcnow(),
                    SatellitePassCache.start_time > datetime.utcnow()  # Only future passes
                )
            ).order_by(SatellitePassCache.start_time).all()
            
            if passes_cache:
                passes_data = [pass_cache.to_dict() for pass_cache in passes_cache]
                # Store in Redis for faster access
                cache.set(redis_key, passes_data, ttl=settings.satellite_passes_cache_ttl)
                logger.debug(f"Pass cache hit (DB) for satellite {norad_id}")
                return passes_data
            
            logger.debug(f"Pass cache miss for satellite {norad_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached passes for satellite {norad_id}: {e}")
            return None
    
    def cache_passes(self, norad_id: int, latitude: float, longitude: float, passes_data: List[Dict[str, Any]]) -> bool:
        """
        Cache satellite pass predictions.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            passes_data: List of pass data from N2YO API
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            # Ensure satellite exists in database
            satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
            if not satellite:
                logger.warning(f"Satellite {norad_id} not found in database, cannot cache passes")
                return False
            
            # Clear existing cache for this location
            self.db.query(SatellitePassCache).filter(
                and_(
                    SatellitePassCache.norad_id == norad_id,
                    SatellitePassCache.latitude == latitude,
                    SatellitePassCache.longitude == longitude
                )
            ).delete()
            
            # Create database cache entries
            cached_passes = []
            for pass_data in passes_data:
                pass_cache = SatellitePassCache.from_n2yo_data(norad_id, latitude, longitude, pass_data)
                self.db.add(pass_cache)
                cached_passes.append(pass_cache.to_dict())
            
            self.db.commit()
            
            # Cache in Redis
            redis_key = f"satellite_passes:{norad_id}:{latitude}:{longitude}"
            cache.set(redis_key, cached_passes, ttl=settings.satellite_passes_cache_ttl)
            
            logger.debug(f"Passes cached for satellite {norad_id} at location ({latitude}, {longitude})")
            return True
            
        except Exception as e:
            logger.error(f"Error caching passes for satellite {norad_id}: {e}")
            self.db.rollback()
            return False
    
    def cleanup_expired_passes(self) -> int:
        """
        Clean up expired pass cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            deleted_count = self.db.query(SatellitePassCache).filter(
                or_(
                    SatellitePassCache.expires_at < datetime.utcnow(),
                    SatellitePassCache.end_time < datetime.utcnow()  # Past passes
                )
            ).delete()
            
            self.db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired pass cache entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired pass cache: {e}")
            self.db.rollback()
            return 0
    
    # General Cache Management
    
    def invalidate_satellite_cache(self, norad_id: int) -> bool:
        """
        Invalidate all cache entries for a specific satellite.
        
        Args:
            norad_id: NORAD ID of the satellite
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        try:
            # Clear Redis cache
            position_key = f"satellite_position:{norad_id}"
            cache.delete(position_key)
            
            # Clear pass cache patterns (this is approximate since Redis doesn't support pattern deletion easily)
            # In a production environment, you might want to use Redis SCAN with pattern matching
            
            # Clear database cache
            self.db.query(SatellitePositionCache).filter(
                SatellitePositionCache.norad_id == norad_id
            ).delete()
            
            self.db.query(SatellitePassCache).filter(
                SatellitePassCache.norad_id == norad_id
            ).delete()
            
            self.db.commit()
            
            logger.info(f"Cache invalidated for satellite {norad_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache for satellite {norad_id}: {e}")
            self.db.rollback()
            return False
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """
        Clean up all expired cache entries.
        
        Returns:
            Dictionary with cleanup counts
        """
        positions_cleaned = self.cleanup_expired_positions()
        passes_cleaned = self.cleanup_expired_passes()
        
        return {
            'positions': positions_cleaned,
            'passes': passes_cleaned,
            'total': positions_cleaned + passes_cleaned
        }