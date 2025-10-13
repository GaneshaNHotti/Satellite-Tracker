"""
Custom exceptions for the Satellite Tracker application.
"""

from typing import Any, Dict, Optional


class SatelliteTrackerException(Exception):
    """Base exception for all application-specific errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(SatelliteTrackerException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=error_details,
            status_code=422
        )


class AuthenticationError(SatelliteTrackerException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details or {},
            status_code=401
        )


class AuthorizationError(SatelliteTrackerException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            details=details or {},
            status_code=403
        )


class NotFoundError(SatelliteTrackerException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, message: str, resource_type: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        
        super().__init__(
            message=message,
            code="NOT_FOUND",
            details=error_details,
            status_code=404
        )


class ConflictError(SatelliteTrackerException):
    """Raised when a resource conflict occurs."""
    
    def __init__(self, message: str, resource_type: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            details=error_details,
            status_code=409
        )


class ExternalAPIError(SatelliteTrackerException):
    """Raised when external API calls fail."""
    
    def __init__(
        self,
        message: str,
        api_name: str = None,
        api_status_code: int = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if api_name:
            error_details["api_name"] = api_name
        if api_status_code:
            error_details["api_status_code"] = api_status_code
        
        super().__init__(
            message=message,
            code="EXTERNAL_API_ERROR",
            details=error_details,
            status_code=502
        )


class DatabaseError(SatelliteTrackerException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details=error_details,
            status_code=500
        )


class CacheError(SatelliteTrackerException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, operation: str = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            details=error_details,
            status_code=500
        )


class RateLimitError(SatelliteTrackerException):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details=error_details,
            status_code=429
        )