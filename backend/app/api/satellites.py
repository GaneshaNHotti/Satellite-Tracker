"""
API endpoints for satellite search and information.
"""

import logging
from datetime import datetime
from typing import List, Optional
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.satellite_service import SatelliteService, get_satellite_service
from app.schemas.satellite import (
    SatelliteInfo,
    SatelliteSearchResponse,
    SatellitePassesResponse,
    SatellitePositionRequest,
    SatellitePassesRequest,
    APIRateLimitStatus,
    ErrorResponse
)
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ExternalAPIError,
    RateLimitExceededError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/satellites", tags=["satellites"])


def handle_satellite_exceptions(func):
    """Decorator to handle common satellite service exceptions."""
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


@router.get(
    "/search",
    response_model=SatelliteSearchResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        502: {"model": ErrorResponse, "description": "External API error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Search satellites by name",
    description="Search for satellites by name using the N2YO API. Results are enhanced with categorization and cached for performance."
)
@handle_satellite_exceptions
async def search_satellites(
    query: str = Query(..., min_length=2, max_length=100, description="Search query (satellite name)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Search for satellites by name.
    
    - **query**: Satellite name to search for (minimum 2 characters)
    - **category**: Optional category filter
    - **limit**: Maximum number of results to return (1-100)
    - **use_cache**: Whether to use cached results for better performance
    
    Returns a list of matching satellites with their basic information.
    """
    logger.info(f"Searching satellites with query: '{query}', category: {category}, limit: {limit}")
    
    satellites = await satellite_service.search_satellites(query, use_cache=use_cache)
    
    # Apply category filter if specified
    if category:
        satellites = [sat for sat in satellites if sat.get("category", "").lower() == category.lower()]
    
    # Apply limit
    satellites = satellites[:limit]
    
    response = SatelliteSearchResponse(
        satellites=[SatelliteInfo(**sat) for sat in satellites],
        total=len(satellites),
        query=query
    )
    
    logger.info(f"Search completed: found {len(satellites)} satellites")
    return response


@router.get(
    "/{norad_id}",
    response_model=SatelliteInfo,
    responses={
        404: {"model": ErrorResponse, "description": "Satellite not found"},
        422: {"model": ErrorResponse, "description": "Invalid NORAD ID"},
        502: {"model": ErrorResponse, "description": "External API error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Get satellite information",
    description="Get detailed information about a specific satellite by its NORAD ID."
)
@handle_satellite_exceptions
async def get_satellite_info(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Get detailed information about a specific satellite.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **use_cache**: Whether to use cached data for better performance
    
    Returns detailed satellite information including name, launch date, country, and category.
    """
    logger.info(f"Getting satellite info for NORAD ID: {norad_id}")
    
    satellite_data = await satellite_service.get_satellite_info(norad_id, use_cache=use_cache)
    
    logger.info(f"Retrieved satellite info for {norad_id}: {satellite_data.get('name', 'Unknown')}")
    return SatelliteInfo(**satellite_data)


@router.get(
    "/{norad_id}/position",
    response_model=SatelliteInfo,
    responses={
        404: {"model": ErrorResponse, "description": "Satellite not found"},
        422: {"model": ErrorResponse, "description": "Invalid parameters"},
        502: {"model": ErrorResponse, "description": "External API error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Get satellite current position",
    description="Get the current position of a satellite as observed from a specific location."
)
@handle_satellite_exceptions
async def get_satellite_position(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    latitude: float = Query(..., ge=-90, le=90, description="Observer latitude in degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Observer longitude in degrees"),
    altitude: float = Query(0, ge=0, le=10000, description="Observer altitude in meters"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Get the current position of a satellite.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **latitude**: Observer latitude in degrees (-90 to 90)
    - **longitude**: Observer longitude in degrees (-180 to 180)
    - **altitude**: Observer altitude in meters (0 to 10000)
    - **use_cache**: Whether to use cached position data (5-minute TTL)
    
    Returns satellite information with current position data.
    """
    logger.info(f"Getting position for satellite {norad_id} from location ({latitude}, {longitude})")
    
    # Get satellite info and position
    satellite_data = await satellite_service.get_satellite_info(norad_id, use_cache=use_cache)
    position_data = await satellite_service.get_satellite_position(
        norad_id, latitude, longitude, altitude, use_cache=use_cache
    )
    
    # Combine satellite info with position
    satellite_data["current_position"] = position_data
    
    logger.info(f"Retrieved position for satellite {norad_id}")
    return SatelliteInfo(**satellite_data)


@router.get(
    "/{norad_id}/passes",
    response_model=SatellitePassesResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Satellite not found"},
        422: {"model": ErrorResponse, "description": "Invalid parameters"},
        502: {"model": ErrorResponse, "description": "External API error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Get satellite pass predictions",
    description="Get upcoming pass predictions for a satellite over a specific location."
)
@handle_satellite_exceptions
async def get_satellite_passes(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    latitude: float = Query(..., ge=-90, le=90, description="Observer latitude in degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Observer longitude in degrees"),
    altitude: float = Query(0, ge=0, le=10000, description="Observer altitude in meters"),
    days: int = Query(10, ge=1, le=10, description="Number of days to predict"),
    min_elevation: float = Query(0, ge=0, le=90, description="Minimum elevation for visible passes"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Get upcoming pass predictions for a satellite.
    
    - **norad_id**: NORAD catalog number (1-999999)
    - **latitude**: Observer latitude in degrees (-90 to 90)
    - **longitude**: Observer longitude in degrees (-180 to 180)
    - **altitude**: Observer altitude in meters (0 to 10000)
    - **days**: Number of days to predict (1-10)
    - **min_elevation**: Minimum elevation angle for visible passes (0-90 degrees)
    - **use_cache**: Whether to use cached pass data (24-hour TTL)
    
    Returns satellite information with upcoming pass predictions.
    """
    logger.info(f"Getting passes for satellite {norad_id} from location ({latitude}, {longitude}) for {days} days")
    
    # Get satellite info and passes
    satellite_data = await satellite_service.get_satellite_info(norad_id, use_cache=use_cache)
    passes_data = await satellite_service.get_satellite_passes(
        norad_id, latitude, longitude, altitude, days, min_elevation, use_cache=use_cache
    )
    
    response = SatellitePassesResponse(
        satellite=SatelliteInfo(**satellite_data),
        location={
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude
        },
        passes=passes_data,
        total=len(passes_data),
        days_predicted=days
    )
    
    logger.info(f"Retrieved {len(passes_data)} passes for satellite {norad_id}")
    return response


@router.get(
    "/status/rate-limit",
    response_model=APIRateLimitStatus,
    summary="Get API rate limit status",
    description="Get the current rate limit status for the N2YO API."
)
async def get_rate_limit_status(
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Get the current rate limit status for the N2YO API.
    
    Returns information about remaining requests and reset time.
    """
    logger.info("Getting API rate limit status")
    
    status = satellite_service.get_api_rate_limit_status()
    
    return APIRateLimitStatus(
        requests_remaining=status.get("requests_remaining"),
        reset_time=status.get("reset_time"),
        api_name="N2YO"
    )


@router.post(
    "/{norad_id}/cache/invalidate",
    summary="Invalidate satellite cache",
    description="Invalidate all cached data for a specific satellite."
)
async def invalidate_satellite_cache(
    norad_id: int = Path(..., description="NORAD catalog number", ge=1, le=999999),
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Invalidate all cached data for a specific satellite.
    
    - **norad_id**: NORAD catalog number (1-999999)
    
    This will force fresh data to be retrieved from the N2YO API on the next request.
    """
    logger.info(f"Invalidating cache for satellite {norad_id}")
    
    success = satellite_service.invalidate_satellite_cache(norad_id)
    
    if success:
        logger.info(f"Cache invalidated for satellite {norad_id}")
        return {"message": f"Cache invalidated for satellite {norad_id}"}
    else:
        logger.error(f"Failed to invalidate cache for satellite {norad_id}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "CACHE_ERROR",
                    "message": f"Failed to invalidate cache for satellite {norad_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@router.post(
    "/cache/cleanup",
    summary="Clean up expired cache",
    description="Clean up all expired cache entries."
)
async def cleanup_expired_cache(
    satellite_service: SatelliteService = Depends(get_satellite_service)
):
    """
    Clean up all expired cache entries.
    
    This removes old position and pass prediction data from the cache.
    """
    logger.info("Cleaning up expired cache entries")
    
    cleanup_stats = satellite_service.cleanup_expired_cache()
    
    logger.info(f"Cache cleanup completed: {cleanup_stats}")
    return {
        "message": "Cache cleanup completed",
        "statistics": cleanup_stats
    }