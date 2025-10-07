"""
Cache cleanup utilities for maintaining cache performance.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from app.database import SessionLocal
from app.services.cache_service import CacheService
from app.redis_client import cache

logger = logging.getLogger(__name__)


class CacheCleanupManager:
    """Manager for cache cleanup operations."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.cache_service = CacheService(self.db)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def cleanup_expired_cache(self) -> Dict[str, Any]:
        """
        Clean up all expired cache entries.
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            logger.info("Starting cache cleanup...")
            start_time = datetime.utcnow()
            
            # Clean up database cache
            cleanup_stats = self.cache_service.cleanup_all_expired()
            
            # Clean up Redis cache (optional - Redis handles TTL automatically)
            # This is mainly for logging purposes
            redis_stats = self._cleanup_redis_cache()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            stats = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'database_cleanup': cleanup_stats,
                'redis_cleanup': redis_stats,
                'success': True
            }
            
            logger.info(f"Cache cleanup completed in {duration:.2f} seconds. "
                       f"Cleaned up {cleanup_stats['total']} database entries.")
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _cleanup_redis_cache(self) -> Dict[str, Any]:
        """
        Clean up Redis cache (mainly for statistics).
        Redis automatically handles TTL expiration.
        
        Returns:
            Dictionary with Redis cleanup statistics
        """
        try:
            # Redis automatically handles TTL, but we can get some stats
            # This is mainly for monitoring purposes
            
            # Note: In a production environment, you might want to implement
            # more sophisticated Redis cleanup using SCAN and pattern matching
            
            return {
                'message': 'Redis handles TTL automatically',
                'manual_cleanup': False
            }
            
        except Exception as e:
            logger.error(f"Redis cache cleanup error: {e}")
            return {
                'error': str(e),
                'manual_cleanup': False
            }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache usage statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            from app.models.cache import SatellitePositionCache, SatellitePassCache
            
            # Database cache statistics
            position_count = self.db.query(SatellitePositionCache).count()
            pass_count = self.db.query(SatellitePassCache).count()
            
            # Recent cache entries (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_positions = self.db.query(SatellitePositionCache).filter(
                SatellitePositionCache.created_at > recent_cutoff
            ).count()
            recent_passes = self.db.query(SatellitePassCache).filter(
                SatellitePassCache.created_at > recent_cutoff
            ).count()
            
            # Expired entries
            position_ttl_cutoff = datetime.utcnow() - timedelta(minutes=5)
            expired_positions = self.db.query(SatellitePositionCache).filter(
                SatellitePositionCache.created_at < position_ttl_cutoff
            ).count()
            
            expired_passes = self.db.query(SatellitePassCache).filter(
                SatellitePassCache.expires_at < datetime.utcnow()
            ).count()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'database_cache': {
                    'total_positions': position_count,
                    'total_passes': pass_count,
                    'recent_positions_24h': recent_positions,
                    'recent_passes_24h': recent_passes,
                    'expired_positions': expired_positions,
                    'expired_passes': expired_passes
                },
                'redis_cache': {
                    'status': 'active' if cache.client.ping() else 'inactive'
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


def run_cache_cleanup():
    """
    Run cache cleanup as a standalone function.
    This can be called from a scheduled job or management command.
    """
    with CacheCleanupManager() as cleanup_manager:
        return cleanup_manager.cleanup_expired_cache()


def get_cache_stats():
    """
    Get cache statistics as a standalone function.
    """
    with CacheCleanupManager() as cleanup_manager:
        return cleanup_manager.get_cache_statistics()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run cleanup
    result = run_cache_cleanup()
    print(f"Cleanup result: {result}")
    
    # Show statistics
    stats = get_cache_stats()
    print(f"Cache statistics: {stats}")