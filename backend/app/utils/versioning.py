"""
API versioning utilities and deprecation handling.
"""

import warnings
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse


class APIVersion:
    """API version information and utilities."""
    
    CURRENT_VERSION = "1.0.0"
    SUPPORTED_VERSIONS = ["1", "1.0", "1.0.0"]  # Support multiple version formats
    DEPRECATED_VERSIONS = []
    
    @classmethod
    def is_supported(cls, version: str) -> bool:
        """
        Check if an API version is supported.
        
        Args:
            version: Version string to check
            
        Returns:
            True if version is supported, False otherwise
        """
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def is_deprecated(cls, version: str) -> bool:
        """
        Check if an API version is deprecated.
        
        Args:
            version: Version string to check
            
        Returns:
            True if version is deprecated, False otherwise
        """
        return version in cls.DEPRECATED_VERSIONS
    
    @classmethod
    def get_version_info(cls, version: str) -> Dict[str, Any]:
        """
        Get information about a specific API version.
        
        Args:
            version: Version string
            
        Returns:
            Dict containing version information
        """
        info = {
            "version": version,
            "supported": cls.is_supported(version),
            "deprecated": cls.is_deprecated(version),
            "current": version == cls.CURRENT_VERSION
        }
        
        if cls.is_deprecated(version):
            info["deprecation_notice"] = f"API version {version} is deprecated. Please upgrade to version {cls.CURRENT_VERSION}."
            info["sunset_date"] = "2024-12-31"  # Example sunset date
        
        return info


def extract_api_version(request: Request) -> str:
    """
    Extract API version from request headers or path.
    
    Args:
        request: FastAPI request object
        
    Returns:
        API version string
    """
    # Check for version in Accept header (e.g., "application/vnd.api+json;version=1.0")
    accept_header = request.headers.get("accept", "")
    if "version=" in accept_header:
        try:
            version_part = accept_header.split("version=")[1].split(";")[0].split(",")[0]
            return normalize_version(version_part.strip())
        except (IndexError, AttributeError):
            pass
    
    # Check for version in custom header
    version_header = request.headers.get("API-Version")
    if version_header:
        return normalize_version(version_header.strip())
    
    # Check for version in path (e.g., /api/v1/...)
    path_parts = request.url.path.split("/")
    for part in path_parts:
        if part.startswith("v") and part[1:].replace(".", "").isdigit():
            return normalize_version(part[1:])  # Remove 'v' prefix
    
    # Default to current version
    return APIVersion.CURRENT_VERSION


def normalize_version(version: str) -> str:
    """
    Normalize version string to a consistent format.
    
    Args:
        version: Version string to normalize
        
    Returns:
        Normalized version string
    """
    # Handle common version formats
    if version == "1":
        return "1"  # Keep as "1" for v1 compatibility
    elif version == "1.0":
        return "1.0"
    elif version == "1.0.0":
        return "1.0.0"
    
    return version


def validate_api_version(version: str) -> None:
    """
    Validate that the requested API version is supported.
    
    Args:
        version: API version to validate
        
    Raises:
        HTTPException: If version is not supported
    """
    if not APIVersion.is_supported(version):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "UNSUPPORTED_API_VERSION",
                    "message": f"API version {version} is not supported",
                    "details": {
                        "requested_version": version,
                        "supported_versions": APIVersion.SUPPORTED_VERSIONS,
                        "current_version": APIVersion.CURRENT_VERSION
                    }
                }
            }
        )


def add_version_headers(response: Response, version: str) -> None:
    """
    Add version-related headers to the response.
    
    Args:
        response: FastAPI response object
        version: API version being used
    """
    response.headers["API-Version"] = version
    response.headers["API-Current-Version"] = APIVersion.CURRENT_VERSION
    response.headers["API-Supported-Versions"] = ",".join(APIVersion.SUPPORTED_VERSIONS)
    
    if APIVersion.is_deprecated(version):
        response.headers["API-Deprecation-Warning"] = f"Version {version} is deprecated"
        response.headers["API-Sunset-Date"] = "2024-12-31"  # Example sunset date


def create_deprecation_warning(version: str) -> Dict[str, Any]:
    """
    Create a deprecation warning for deprecated API versions.
    
    Args:
        version: Deprecated API version
        
    Returns:
        Dict containing deprecation warning
    """
    return {
        "warning": {
            "code": "DEPRECATED_API_VERSION",
            "message": f"API version {version} is deprecated and will be removed in the future",
            "details": {
                "deprecated_version": version,
                "current_version": APIVersion.CURRENT_VERSION,
                "sunset_date": "2024-12-31",
                "migration_guide": f"/api/docs/migration/v{version}-to-v{APIVersion.CURRENT_VERSION}"
            }
        }
    }


class VersioningMiddleware:
    """
    Middleware for handling API versioning and deprecation warnings.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """
        Process request and add version handling.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Create request object to extract version
        request = Request(scope, receive)
        version = extract_api_version(request)
        
        # Validate version
        try:
            validate_api_version(version)
        except HTTPException as e:
            # Send error response
            response = JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
            await response(scope, receive, send)
            return
        
        # Store version in scope for use by endpoints
        scope["api_version"] = version
        
        # Create custom send function to add headers
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add version headers
                headers[b"api-version"] = version.encode()
                headers[b"api-current-version"] = APIVersion.CURRENT_VERSION.encode()
                headers[b"api-supported-versions"] = ",".join(APIVersion.SUPPORTED_VERSIONS).encode()
                
                if APIVersion.is_deprecated(version):
                    headers[b"api-deprecation-warning"] = f"Version {version} is deprecated".encode()
                    headers[b"api-sunset-date"] = b"2024-12-31"
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_with_headers)