"""
API endpoints for enhanced satellite position tracking and pass predictions.
Provides real-time position tracking, pass predictions, and background task management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.position_tracking_service import PositionTrackingService, get_position_tracking_service
from app.services.pass_prediction_service import PassPredictionService, get_pass_prediction_service
from app.services.background_tasks import BackgroundTaskService, get_background_task_service
from app.utils.dependencies import get_current_user
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ExternalAPIError,
    RateLimitExceededError
)
from app.schemas.satellite import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


def handle_tracking_exceptions(func):
    """Decorator to handle common tracking service exceptions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except RateLimitExceededError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except ExternalAPIError as e:
            logger.error(f"External API error: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {"error": str(e)},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
    return wrapper


# Position Tracking Endpoints

@router.get(
    "/satellites/{norad_id}/position/realtime",
    summary="Get real-time satellite position",
    description="Get enhanced real-time position data for a satellite with additional calculations and formatting."
)
@handle_tracking_exceptions
async def get_realtime_position(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    latitude: float = Query(..., ge=-90, le=90, description="Observer latitude in degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Observer longitude in degrees"),
    altitude: float = Query(0, ge=0, le=10000, description="Observer altitude in meters"),
    force_refresh: bool = Query(False, description="Force fresh data from API"),
    position_service: PositionTrackingService = Depends(get_position_tracking_service)
):
    """
    Get enhanced real-time satellite position with additional calculations.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **latitude**: Observer latitude in degrees (-90 to 90)
    - **longitude**: Observer longitude in degrees (-180 to 180)
    - **altitude**: Observer altitude in meters (0 to 10000)
    - **force_refresh**: Force fresh data from API (bypasses cache)
    
    Returns enhanced position data with distance calculations, visibility info, and coordinate formatting.
    """
    logger.info(f"Getting real-time position for satellite {norad_id} from ({latitude}, {longitude})")
    
    position_data = await position_service.get_real_time_position(
        norad_id, latitude, longitude, altitude, force_refresh
    )
    
    return {
        "norad_id": norad_id,
        "position": position_data,
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/satellites/{norad_id}/position/history",
    summary="Get satellite position history",
    description="Get historical position data for a satellite from cache."
)
@handle_tracking_exceptions
async def get_position_history(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    hours: int = Query(24, ge=1, le=168, description="Number of hours of history"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    position_service: PositionTrackingService = Depends(get_position_tracking_service)
):
    """
    Get historical position data for a satellite.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **hours**: Number of hours of history to retrieve (1-168)
    - **limit**: Maximum number of position records (1-500)
    
    Returns list of historical position data with timestamps.
    """
    logger.info(f"Getting position history for satellite {norad_id} ({hours} hours, limit {limit})")
    
    history = position_service.get_position_history(norad_id, hours, limit)
    
    return {
        "norad_id": norad_id,
        "history": history,
        "total_records": len(history),
        "hours_requested": hours
    }


@router.get(
    "/users/favorites/positions",
    summary="Get positions for all favorite satellites",
    description="Get current positions for all user's favorite satellites."
)
@handle_tracking_exceptions
async def get_favorite_positions(
    force_refresh: bool = Query(False, description="Force fresh data from API"),
    current_user: dict = Depends(get_current_user),
    position_service: PositionTrackingService = Depends(get_position_tracking_service)
):
    """
    Get current positions for all user's favorite satellites.
    
    - **force_refresh**: Force fresh data from API (bypasses cache)
    
    Returns list of favorite satellites with current position data.
    Requires user authentication and saved location.
    """
    logger.info(f"Getting favorite positions for user {current_user['id']}")
    
    favorites_with_positions = await position_service.get_favorite_positions(
        current_user["id"], force_refresh
    )
    
    return {
        "user_id": current_user["id"],
        "favorites": favorites_with_positions,
        "total_favorites": len(favorites_with_positions),
        "retrieved_at": datetime.utcnow().isoformat()
    }


# Pass Prediction Endpoints

@router.get(
    "/satellites/{norad_id}/passes",
    summary="Get enhanced satellite pass predictions",
    description="Get enhanced pass predictions with filtering, sorting, and additional calculations."
)
@handle_tracking_exceptions
async def get_satellite_passes(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    latitude: float = Query(..., ge=-90, le=90, description="Observer latitude in degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Observer longitude in degrees"),
    altitude: float = Query(0, ge=0, le=10000, description="Observer altitude in meters"),
    days: int = Query(10, ge=1, le=10, description="Number of days to predict"),
    min_elevation: float = Query(0, ge=0, le=90, description="Minimum elevation for passes"),
    visibility_filter: str = Query("all", description="Filter by visibility (all, visible, bright)"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    pass_service: PassPredictionService = Depends(get_pass_prediction_service)
):
    """
    Get enhanced satellite pass predictions with filtering and sorting.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **latitude**: Observer latitude in degrees (-90 to 90)
    - **longitude**: Observer longitude in degrees (-180 to 180)
    - **altitude**: Observer altitude in meters (0 to 10000)
    - **days**: Number of days to predict (1-10)
    - **min_elevation**: Minimum elevation angle for passes (0-90 degrees)
    - **visibility_filter**: Filter by visibility ("all", "visible", "bright")
    - **use_cache**: Whether to use cached pass data
    
    Returns enhanced pass predictions with visibility quality, priority scores, and timing information.
    """
    logger.info(f"Getting enhanced passes for satellite {norad_id} from ({latitude}, {longitude})")
    
    passes = await pass_service.get_satellite_passes(
        norad_id, latitude, longitude, altitude, days, min_elevation, visibility_filter, use_cache
    )
    
    return {
        "norad_id": norad_id,
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude
        },
        "passes": passes,
        "total_passes": len(passes),
        "days_predicted": days,
        "filters": {
            "min_elevation": min_elevation,
            "visibility_filter": visibility_filter
        }
    }


@router.get(
    "/users/passes",
    summary="Get passes for all favorite satellites",
    description="Get pass predictions for all user's favorite satellites with enhanced filtering."
)
@handle_tracking_exceptions
async def get_user_passes(
    days: int = Query(10, ge=1, le=10, description="Number of days to predict"),
    min_elevation: float = Query(10, ge=0, le=90, description="Minimum elevation for passes"),
    visibility_filter: str = Query("visible", description="Filter by visibility (all, visible, bright)"),
    max_passes_per_satellite: int = Query(5, ge=1, le=20, description="Maximum passes per satellite"),
    current_user: dict = Depends(get_current_user),
    pass_service: PassPredictionService = Depends(get_pass_prediction_service)
):
    """
    Get pass predictions for all user's favorite satellites.
    
    - **days**: Number of days to predict (1-10)
    - **min_elevation**: Minimum elevation angle for passes (0-90 degrees)
    - **visibility_filter**: Filter by visibility ("all", "visible", "bright")
    - **max_passes_per_satellite**: Maximum passes per satellite (1-20)
    
    Returns combined pass predictions for all favorite satellites, sorted by time and priority.
    Requires user authentication and saved location.
    """
    logger.info(f"Getting passes for all favorites for user {current_user['id']}")
    
    all_passes = await pass_service.get_all_favorite_passes(
        current_user["id"], days, min_elevation, visibility_filter, max_passes_per_satellite
    )
    
    return {
        "user_id": current_user["id"],
        "passes": all_passes,
        "total_passes": len(all_passes),
        "days_predicted": days,
        "filters": {
            "min_elevation": min_elevation,
            "visibility_filter": visibility_filter,
            "max_passes_per_satellite": max_passes_per_satellite
        }
    }


@router.get(
    "/users/passes/upcoming",
    summary="Get upcoming passes (fast lookup)",
    description="Get upcoming passes for user's favorites from cache for fast lookup."
)
@handle_tracking_exceptions
async def get_upcoming_passes(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look ahead"),
    min_elevation: float = Query(10, ge=0, le=90, description="Minimum elevation for passes"),
    current_user: dict = Depends(get_current_user),
    pass_service: PassPredictionService = Depends(get_pass_prediction_service)
):
    """
    Get upcoming passes for user's favorites from cache (fast lookup).
    
    - **hours**: Number of hours to look ahead (1-168)
    - **min_elevation**: Minimum elevation angle for passes (0-90 degrees)
    
    Returns upcoming passes from cache for fast response times.
    Requires user authentication and saved location.
    """
    logger.info(f"Getting upcoming passes for user {current_user['id']} ({hours} hours)")
    
    upcoming_passes = pass_service.get_upcoming_passes(
        current_user["id"], hours, min_elevation
    )
    
    return {
        "user_id": current_user["id"],
        "upcoming_passes": upcoming_passes,
        "total_passes": len(upcoming_passes),
        "hours_ahead": hours,
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/users/passes/alerts",
    summary="Get pass alerts",
    description="Get passes that should trigger alerts based on timing."
)
@handle_tracking_exceptions
async def get_pass_alerts(
    alert_minutes: List[int] = Query([60, 15, 5], description="Minutes before pass to trigger alerts"),
    current_user: dict = Depends(get_current_user),
    pass_service: PassPredictionService = Depends(get_pass_prediction_service)
):
    """
    Get passes that should trigger alerts based on timing.
    
    - **alert_minutes**: List of minutes before pass to trigger alerts
    
    Returns passes requiring alerts with timing information.
    Requires user authentication and saved location.
    """
    logger.info(f"Getting pass alerts for user {current_user['id']}")
    
    alerts = pass_service.get_pass_alerts(current_user["id"], alert_minutes)
    
    return {
        "user_id": current_user["id"],
        "alerts": alerts,
        "total_alerts": len(alerts),
        "alert_minutes": alert_minutes,
        "generated_at": datetime.utcnow().isoformat()
    }


# Background Task Management Endpoints

@router.post(
    "/background/refresh-positions",
    summary="Manually refresh all positions",
    description="Manually trigger a refresh of all favorite satellite positions."
)
@handle_tracking_exceptions
async def manual_refresh_positions(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    task_service: BackgroundTaskService = Depends(get_background_task_service)
):
    """
    Manually trigger a refresh of all favorite satellite positions.
    
    This endpoint triggers a background refresh of position data for all satellites
    that are in users' favorites lists.
    """
    logger.info(f"Manual position refresh requested by user {current_user['id']}")
    
    # Add background task
    background_tasks.add_task(task_service.manual_refresh_all_positions)
    
    return {
        "message": "Position refresh started",
        "status": "background_task_queued",
        "requested_by": current_user["id"],
        "requested_at": datetime.utcnow().isoformat()
    }


@router.post(
    "/background/cleanup-cache",
    summary="Manually cleanup cache",
    description="Manually trigger cleanup of expired cache entries."
)
@handle_tracking_exceptions
async def manual_cleanup_cache(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    task_service: BackgroundTaskService = Depends(get_background_task_service)
):
    """
    Manually trigger cleanup of expired cache entries.
    
    This endpoint triggers a background cleanup of expired position and pass cache data.
    """
    logger.info(f"Manual cache cleanup requested by user {current_user['id']}")
    
    # Add background task
    background_tasks.add_task(task_service.manual_cleanup_cache)
    
    return {
        "message": "Cache cleanup started",
        "status": "background_task_queued",
        "requested_by": current_user["id"],
        "requested_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/background/status",
    summary="Get background task status",
    description="Get status of all background tasks."
)
async def get_background_task_status(
    task_service: BackgroundTaskService = Depends(get_background_task_service)
):
    """
    Get status of all background tasks.
    
    Returns information about running background tasks and their status.
    """
    status = task_service.get_task_status()
    
    return {
        "tasks": status,
        "checked_at": datetime.utcnow().isoformat()
    }


@router.post(
    "/cache/optimize",
    summary="Optimize pass cache",
    description="Optimize pass cache by pre-computing passes for popular locations."
)
@handle_tracking_exceptions
async def optimize_pass_cache(
    location_radius_km: float = Query(50, ge=1, le=500, description="Radius around user locations"),
    current_user: dict = Depends(get_current_user),
    pass_service: PassPredictionService = Depends(get_pass_prediction_service)
):
    """
    Optimize pass cache by pre-computing passes for popular locations.
    
    - **location_radius_km**: Radius around user locations to consider (1-500 km)
    
    This endpoint analyzes user locations and pre-caches pass predictions for popular areas.
    """
    logger.info(f"Cache optimization requested by user {current_user['id']}")
    
    optimization_stats = pass_service.optimize_pass_cache(location_radius_km)
    
    return {
        "message": "Cache optimization completed",
        "statistics": optimization_stats,
        "optimized_by": current_user["id"],
        "optimized_at": datetime.utcnow().isoformat()
    }