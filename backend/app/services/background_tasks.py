"""
Background task service for automatic satellite data refresh and maintenance.
Provides scheduled tasks for position updates, cache cleanup, and data maintenance.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.database import get_db
from app.services.position_tracking_service import PositionTrackingService
from app.services.cache_service import CacheService
from app.models.favorite import UserFavoriteSatellite
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """
    Service for managing background tasks related to satellite data maintenance.
    Handles automatic position refresh, cache cleanup, and data synchronization.
    """
    
    def __init__(self):
        self.running_tasks = {}
        self.task_intervals = {
            "position_refresh": 300,  # 5 minutes
            "cache_cleanup": 3600,    # 1 hour
            "stale_data_refresh": 600  # 10 minutes
        }
    
    @asynccontextmanager
    async def get_db_session(self):
        """Get database session for background tasks."""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
    
    async def start_position_refresh_task(self) -> None:
        """
        Start the automatic position refresh background task.
        Refreshes positions for satellites that are in users' favorites.
        """
        if "position_refresh" in self.running_tasks:
            logger.warning("Position refresh task is already running")
            return
        
        async def position_refresh_loop():
            logger.info("Starting position refresh background task")
            
            while True:
                try:
                    await self._refresh_favorite_positions()
                    await asyncio.sleep(self.task_intervals["position_refresh"])
                except asyncio.CancelledError:
                    logger.info("Position refresh task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in position refresh task: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        task = asyncio.create_task(position_refresh_loop())
        self.running_tasks["position_refresh"] = task
        logger.info("Position refresh task started")
    
    async def start_cache_cleanup_task(self) -> None:
        """
        Start the automatic cache cleanup background task.
        Removes expired cache entries and optimizes database performance.
        """
        if "cache_cleanup" in self.running_tasks:
            logger.warning("Cache cleanup task is already running")
            return
        
        async def cache_cleanup_loop():
            logger.info("Starting cache cleanup background task")
            
            while True:
                try:
                    await self._cleanup_expired_cache()
                    await asyncio.sleep(self.task_intervals["cache_cleanup"])
                except asyncio.CancelledError:
                    logger.info("Cache cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying
        
        task = asyncio.create_task(cache_cleanup_loop())
        self.running_tasks["cache_cleanup"] = task
        logger.info("Cache cleanup task started")
    
    async def start_stale_data_refresh_task(self) -> None:
        """
        Start the stale data refresh background task.
        Proactively refreshes data that is approaching expiration.
        """
        if "stale_data_refresh" in self.running_tasks:
            logger.warning("Stale data refresh task is already running")
            return
        
        async def stale_data_refresh_loop():
            logger.info("Starting stale data refresh background task")
            
            while True:
                try:
                    await self._refresh_stale_data()
                    await asyncio.sleep(self.task_intervals["stale_data_refresh"])
                except asyncio.CancelledError:
                    logger.info("Stale data refresh task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in stale data refresh task: {e}")
                    await asyncio.sleep(120)  # Wait 2 minutes before retrying
        
        task = asyncio.create_task(stale_data_refresh_loop())
        self.running_tasks["stale_data_refresh"] = task
        logger.info("Stale data refresh task started")
    
    async def stop_task(self, task_name: str) -> bool:
        """
        Stop a specific background task.
        
        Args:
            task_name: Name of the task to stop
            
        Returns:
            True if task was stopped, False if task wasn't running
        """
        if task_name not in self.running_tasks:
            logger.warning(f"Task {task_name} is not running")
            return False
        
        task = self.running_tasks[task_name]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.running_tasks[task_name]
        logger.info(f"Task {task_name} stopped")
        return True
    
    async def stop_all_tasks(self) -> None:
        """Stop all running background tasks."""
        tasks_to_stop = list(self.running_tasks.keys())
        
        for task_name in tasks_to_stop:
            await self.stop_task(task_name)
        
        logger.info("All background tasks stopped")
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        Get status of all background tasks.
        
        Returns:
            Dictionary with task status information
        """
        status = {}
        
        for task_name, interval in self.task_intervals.items():
            is_running = task_name in self.running_tasks
            task_info = {
                "running": is_running,
                "interval_seconds": interval,
                "next_run": None
            }
            
            if is_running:
                task = self.running_tasks[task_name]
                task_info["done"] = task.done()
                task_info["cancelled"] = task.cancelled()
            
            status[task_name] = task_info
        
        return status
    
    async def _refresh_favorite_positions(self) -> Dict[str, int]:
        """
        Refresh positions for satellites in users' favorites.
        
        Returns:
            Dictionary with refresh statistics
        """
        async with self.get_db_session() as db:
            position_service = PositionTrackingService(db)
            
            # Get all unique NORAD IDs from favorites
            favorite_norad_ids = db.query(UserFavoriteSatellite.norad_id).distinct().all()
            norad_ids = [fav.norad_id for fav in favorite_norad_ids]
            
            if not norad_ids:
                logger.debug("No favorite satellites to refresh")
                return {"refreshed": 0, "failed": 0, "total": 0}
            
            # Get a representative location for position calculations
            # Use the first user with a location, or default to New York
            default_lat, default_lon = 40.7128, -74.0060
            
            user_with_location = db.query(User).filter(User.locations.any()).first()
            if user_with_location and user_with_location.locations:
                location = user_with_location.locations[-1]
                default_lat = float(location.latitude)
                default_lon = float(location.longitude)
            
            # Refresh positions in batches
            batch_size = 5
            total_refreshed = 0
            total_failed = 0
            
            for i in range(0, len(norad_ids), batch_size):
                batch = norad_ids[i:i + batch_size]
                
                try:
                    positions = await position_service.get_multiple_positions(
                        batch, default_lat, default_lon
                    )
                    total_refreshed += len(positions)
                    total_failed += len(batch) - len(positions)
                except Exception as e:
                    logger.error(f"Error refreshing position batch: {e}")
                    total_failed += len(batch)
                
                # Small delay between batches to avoid overwhelming the API
                await asyncio.sleep(1)
            
            logger.info(f"Position refresh completed: {total_refreshed} refreshed, {total_failed} failed")
            return {"refreshed": total_refreshed, "failed": total_failed, "total": len(norad_ids)}
    
    async def _cleanup_expired_cache(self) -> Dict[str, int]:
        """
        Clean up expired cache entries.
        
        Returns:
            Dictionary with cleanup statistics
        """
        async with self.get_db_session() as db:
            cache_service = CacheService(db)
            
            cleanup_stats = cache_service.cleanup_all_expired()
            
            logger.info(f"Cache cleanup completed: {cleanup_stats}")
            return cleanup_stats
    
    async def _refresh_stale_data(self) -> Dict[str, int]:
        """
        Refresh data that is approaching expiration.
        
        Returns:
            Dictionary with refresh statistics
        """
        async with self.get_db_session() as db:
            position_service = PositionTrackingService(db)
            
            # Refresh positions that are older than 3 minutes (before 5-minute expiry)
            refresh_stats = await position_service.refresh_stale_positions(
                max_age_minutes=3, batch_size=10
            )
            
            logger.debug(f"Stale data refresh completed: {refresh_stats}")
            return refresh_stats
    
    async def manual_refresh_all_positions(self) -> Dict[str, Any]:
        """
        Manually trigger a full refresh of all favorite satellite positions.
        
        Returns:
            Dictionary with refresh results
        """
        logger.info("Starting manual refresh of all positions")
        
        start_time = datetime.utcnow()
        refresh_stats = await self._refresh_favorite_positions()
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "statistics": refresh_stats
        }
        
        logger.info(f"Manual refresh completed in {duration:.2f} seconds")
        return result
    
    async def manual_cleanup_cache(self) -> Dict[str, Any]:
        """
        Manually trigger cache cleanup.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting manual cache cleanup")
        
        start_time = datetime.utcnow()
        cleanup_stats = await self._cleanup_expired_cache()
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "statistics": cleanup_stats
        }
        
        logger.info(f"Manual cache cleanup completed in {duration:.2f} seconds")
        return result


# Global instance
background_task_service = BackgroundTaskService()


# Dependency function for FastAPI
def get_background_task_service() -> BackgroundTaskService:
    """Dependency function to get background task service instance."""
    return background_task_service