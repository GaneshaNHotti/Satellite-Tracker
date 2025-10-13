"""
Custom exception classes for the satellite tracker application.
"""

from typing import Optional, Dict, Any


class SatelliteTrackerException(Exception):
    """Base exception class for satellite tracker application."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SatelliteTrackerException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", error_details)


class AuthenticationError(SatelliteTrackerException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(SatelliteTrackerException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class NotFoundError(SatelliteTrackerException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, "NOT_FOUND", details)


class ExternalAPIError(SatelliteTrackerException):
    """Exception raised for external API errors."""
    
    def __init__(self, message: str, api_name: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if api_name:
            error_details["api_name"] = api_name
        if status_code:
            error_details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_API_ERROR", error_details)


class RateLimitExceededError(SatelliteTrackerException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", reset_time: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if reset_time:
            error_details["reset_time"] = reset_time
        super().__init__(message, "RATE_LIMIT_EXCEEDED", error_details)


class CacheError(SatelliteTrackerException):
    """Exception raised for cache-related errors."""
    
    def __init__(self, message: str, cache_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if cache_key:
            error_details["cache_key"] = cache_key
        super().__init__(message, "CACHE_ERROR", error_details)


class DatabaseError(SatelliteTrackerException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        super().__init__(message, "DATABASE_ERROR", error_details)


class ConfigurationError(SatelliteTrackerException):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        super().__init__(message, "CONFIGURATION_ERROR", error_details)