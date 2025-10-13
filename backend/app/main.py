from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.location import router as location_router
from app.api.satellites import router as satellites_router
from app.api.favorites import router as favorites_router
from app.api.tracking import router as tracking_router
from app.api.health import router as health_router
from app.config import settings
from app.middleware.auth_middleware import AuthenticationMiddleware, RateLimitMiddleware
from app.middleware.error_handler import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    create_exception_handlers
)
from app.services.background_tasks import background_task_service
from app.utils.logging_config import setup_logging, get_logger
from app.utils.api_docs import custom_openapi_schema
from app.utils.versioning import VersioningMiddleware
from app.redis_client import redis_client

# Set up logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Satellite Tracker & Alerts Platform API",
    description="""
    A comprehensive API for tracking satellites in real-time and managing satellite pass predictions.
    
    ## Features
    
    * **User Authentication**: Register and login with JWT token-based authentication
    * **Location Management**: Save and manage user locations for pass predictions
    * **Satellite Search**: Search for satellites by name or NORAD ID
    * **Favorites Management**: Add satellites to favorites for quick access
    * **Real-time Tracking**: Get current satellite positions and pass predictions
    * **Caching**: Optimized performance with Redis caching
    
    ## External Dependencies
    
    This API integrates with the [N2YO API](https://www.n2yo.com/api/) for satellite data.
    
    ## Rate Limiting
    
    API endpoints are rate-limited to ensure fair usage:
    - Authentication endpoints: 5 requests per 5 minutes
    - General API endpoints: 100 requests per minute
    - Search endpoints: 20 requests per minute
    
    ## Error Handling
    
    All errors follow a consistent format with correlation IDs for tracking.
    """,
    version="1.0.0",
    contact={
        "name": "Satellite Tracker API Support",
        "email": "support@satellitetracker.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)

# Add exception handlers
exception_handlers = create_exception_handlers()
for exception_type, handler in exception_handlers.items():
    app.add_exception_handler(exception_type, handler)

# Add middleware (order matters - add in reverse order of execution)
# Error handling middleware should be first to catch all exceptions
app.add_middleware(ErrorHandlingMiddleware, debug=settings.debug)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware, log_requests=True, log_responses=True)

# Authentication middleware
app.add_middleware(AuthenticationMiddleware)

# Rate limiting middleware with Redis support
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# API versioning middleware
app.add_middleware(VersioningMiddleware)

# CORS middleware should be last
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "API-Version",
        "X-Requested-With",
        "X-Correlation-ID"
    ],
    expose_headers=[
        "API-Version",
        "API-Current-Version", 
        "API-Supported-Versions",
        "API-Deprecation-Warning",
        "API-Sunset-Date",
        "X-Correlation-ID",
        "X-Process-Time"
    ],
    max_age=86400,  # 24 hours
)

app.include_router(health_router)  # Health endpoints at root level
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(location_router, prefix=settings.api_v1_prefix)
app.include_router(satellites_router, prefix=settings.api_v1_prefix)
app.include_router(favorites_router, prefix=settings.api_v1_prefix)
app.include_router(tracking_router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Satellite Tracker API",
        "version": "1.0.0",
        "docs_url": "/api/docs",
        "health_url": "/health"
    }


# Set custom OpenAPI schema
app.openapi = lambda: custom_openapi_schema(app)


@app.get("/api/version", tags=["API Info"])
async def get_api_version():
    """Get API version information."""
    from app.utils.versioning import APIVersion
    return {
        "current_version": APIVersion.CURRENT_VERSION,
        "supported_versions": APIVersion.SUPPORTED_VERSIONS,
        "deprecated_versions": APIVersion.DEPRECATED_VERSIONS
    }


@app.get("/api/info", tags=["API Info"])
async def get_api_info():
    """Get comprehensive API information."""
    return {
        "name": "Satellite Tracker & Alerts Platform API",
        "version": "1.0.0",
        "description": "API for tracking satellites and managing user favorites",
        "documentation": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_spec": "/api/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "version": "/api/version"
        },
        "external_dependencies": {
            "n2yo_api": "https://www.n2yo.com/api/"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    logger.info("Starting Satellite Tracker API v1.0.0...")
    logger.info("Starting background tasks...")
    await background_task_service.start_position_refresh_task()
    await background_task_service.start_cache_cleanup_task()
    await background_task_service.start_stale_data_refresh_task()
    logger.info("Background tasks started")
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown."""
    logger.info("Shutting down Satellite Tracker API...")
    logger.info("Stopping background tasks...")
    await background_task_service.stop_all_tasks()
    logger.info("Background tasks stopped")
    logger.info("API shutdown complete")