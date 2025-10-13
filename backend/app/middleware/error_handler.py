"""
Global error handling middleware and exception handlers for FastAPI.
"""

import logging
import traceback
import time
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError

from app.exceptions import (
    SatelliteTrackerException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ExternalAPIError,
    DatabaseError,
    CacheError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response format."""
    
    @staticmethod
    def create_error_response(
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        status_code: int = 500
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            code: Error code identifier
            message: Human-readable error message
            details: Additional error details
            correlation_id: Request correlation ID for tracking
            status_code: HTTP status code
            
        Returns:
            Dict containing the standardized error response
        """
        error_response = {
            "error": {
                "code": code,
                "message": message,
                "timestamp": time.time(),
                "status_code": status_code
            }
        }
        
        if details:
            error_response["error"]["details"] = details
            
        if correlation_id:
            error_response["error"]["correlation_id"] = correlation_id
            
        return error_response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling uncaught exceptions and providing consistent error responses.
    """
    
    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and handle any uncaught exceptions.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        try:
            response = await call_next(request)
            
            # Add correlation ID to successful responses
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Log the error with correlation ID
            logger.error(
                f"Unhandled exception in request {correlation_id}: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "exception_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Create error response
            if isinstance(e, SatelliteTrackerException):
                error_response = ErrorResponse.create_error_response(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                    correlation_id=correlation_id,
                    status_code=e.status_code
                )
                status_code = e.status_code
            else:
                # Handle unexpected exceptions
                error_response = ErrorResponse.create_error_response(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected error occurred. Please try again later.",
                    details={"exception_type": type(e).__name__} if self.debug else None,
                    correlation_id=correlation_id,
                    status_code=500
                )
                status_code = 500
            
            return JSONResponse(
                status_code=status_code,
                content=error_response,
                headers={"X-Correlation-ID": correlation_id}
            )


def create_exception_handlers():
    """
    Create FastAPI exception handlers for various error types.
    
    Returns:
        Dict of exception handlers
    """
    
    async def satellite_tracker_exception_handler(request: Request, exc: SatelliteTrackerException):
        """Handle custom application exceptions."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        logger.warning(
            f"Application exception in request {correlation_id}: {exc.code} - {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.code,
                "error_details": exc.details
            }
        )
        
        error_response = ErrorResponse.create_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
            status_code=exc.status_code
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        logger.warning(
            f"HTTP exception in request {correlation_id}: {exc.status_code} - {exc.detail}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        # Map HTTP status codes to error codes
        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE"
        }
        
        error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
        
        error_response = ErrorResponse.create_error_response(
            code=error_code,
            message=exc.detail,
            correlation_id=correlation_id,
            status_code=exc.status_code
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        # Extract validation error details
        validation_errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation error in request {correlation_id}: {len(validation_errors)} validation errors",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "validation_errors": validation_errors
            }
        )
        
        error_response = ErrorResponse.create_error_response(
            code="VALIDATION_ERROR",
            message="Input validation failed",
            details={"validation_errors": validation_errors},
            correlation_id=correlation_id,
            status_code=422
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle SQLAlchemy database errors."""
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        logger.error(
            f"Database error in request {correlation_id}: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__
            },
            exc_info=True
        )
        
        # Handle specific SQLAlchemy errors
        if isinstance(exc, IntegrityError):
            error_response = ErrorResponse.create_error_response(
                code="INTEGRITY_ERROR",
                message="Data integrity constraint violation",
                details={"constraint_type": "database_constraint"},
                correlation_id=correlation_id,
                status_code=409
            )
            status_code = 409
        else:
            error_response = ErrorResponse.create_error_response(
                code="DATABASE_ERROR",
                message="Database operation failed",
                correlation_id=correlation_id,
                status_code=500
            )
            status_code = 500
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={"X-Correlation-ID": correlation_id}
        )
    
    return {
        SatelliteTrackerException: satellite_tracker_exception_handler,
        HTTPException: http_exception_handler,
        StarletteHTTPException: http_exception_handler,
        RequestValidationError: validation_exception_handler,
        SQLAlchemyError: sqlalchemy_exception_handler,
    }


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and responses.
    """
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Log request and response information.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
        
        # Log incoming request
        if self.log_requests:
            logger.info(
                f"Incoming request {correlation_id}: {request.method} {request.url.path}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent")
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        if self.log_responses:
            logger.info(
                f"Response for request {correlation_id}: {response.status_code} in {process_time:.3f}s",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "response_size": response.headers.get("content-length")
                }
            )
        
        # Add processing time header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response