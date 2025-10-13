"""
Health check and monitoring endpoints.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.redis_client import redis_client
from app.services.n2yo_service import N2YOService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Dict with basic health status
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with dependency status.
    
    Args:
        db: Database session
        
    Returns:
        Dict with detailed health information
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database health check
    try:
        start_time = time.time()
        db.execute(text("SELECT 1"))
        db_response_time = time.time() - start_time
        
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time": round(db_response_time * 1000, 2),  # ms
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
        overall_healthy = False
    
    # Redis health check
    try:
        if redis_client:
            start_time = time.time()
            await redis_client.ping()
            redis_response_time = time.time() - start_time
            
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "response_time": round(redis_response_time * 1000, 2),  # ms
                "message": "Redis connection successful"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "unavailable",
                "message": "Redis client not configured"
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Redis connection failed"
        }
        # Redis failure is not critical for basic functionality
    
    # N2YO API health check
    try:
        n2yo_service = N2YOService()
        start_time = time.time()
        # Try a simple API call to check connectivity
        await n2yo_service._make_request("/satellites/above/41.702/-76.014/0/70/18/")
        api_response_time = time.time() - start_time
        
        health_status["checks"]["n2yo_api"] = {
            "status": "healthy",
            "response_time": round(api_response_time * 1000, 2),  # ms
            "message": "N2YO API accessible"
        }
    except Exception as e:
        logger.warning(f"N2YO API health check failed: {str(e)}")
        health_status["checks"]["n2yo_api"] = {
            "status": "degraded",
            "error": str(e),
            "message": "N2YO API may be unavailable"
        }
        # External API failure is not critical for basic functionality
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    elif any(check.get("status") == "degraded" for check in health_status["checks"].values()):
        health_status["status"] = "degraded"
    
    # Return appropriate HTTP status
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status


@router.get("/health/readiness", tags=["Health"])
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Dict with readiness status
    """
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@router.get("/health/liveness", tags=["Health"])
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Returns:
        Dict with liveness status
    """
    return {
        "status": "alive",
        "timestamp": time.time()
    }


@router.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Basic application metrics endpoint.
    
    Returns:
        Dict with application metrics
    """
    # In a production environment, you would integrate with
    # Prometheus or another metrics system
    return {
        "timestamp": time.time(),
        "uptime": time.time(),  # Would track actual uptime
        "requests_total": 0,    # Would track total requests
        "errors_total": 0,      # Would track total errors
        "active_connections": 0  # Would track active connections
    }


@router.get("/status", tags=["Health"])
async def get_api_status():
    """
    Comprehensive API status endpoint.
    
    Returns:
        Dict with API status and configuration information
    """
    from app.config import settings
    from app.utils.versioning import APIVersion
    
    return {
        "api": {
            "name": "Satellite Tracker & Alerts Platform API",
            "version": APIVersion.CURRENT_VERSION,
            "status": "operational",
            "environment": settings.environment,
            "debug_mode": settings.debug
        },
        "features": {
            "authentication": True,
            "rate_limiting": settings.rate_limit_enabled,
            "caching": True,
            "real_time_tracking": True,
            "pass_predictions": True
        },
        "external_services": {
            "n2yo_api": {
                "name": "N2YO Satellite API",
                "url": settings.n2yo_base_url,
                "status": "unknown"  # Would check in production
            }
        },
        "documentation": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_spec": "/api/openapi.json"
        },
        "timestamp": time.time()
    }