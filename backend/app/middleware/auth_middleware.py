"""
Authentication middleware for FastAPI application.
"""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

from app.utils.auth import is_token_expired
from app.services.token_blacklist_service import TokenBlacklistService

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication-related concerns.
    
    This middleware:
    - Logs authentication attempts
    - Handles token expiration gracefully
    - Provides consistent error responses
    """
    
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh"
        ]
        self.blacklist_service = TokenBlacklistService()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and handle authentication concerns.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        start_time = time.time()
        
        # Skip authentication middleware for excluded paths
        if request.url.path in self.excluded_paths:
            response = await call_next(request)
            return response
        
        # Extract authorization header
        auth_header = request.headers.get("authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Check if token is expired and provide clear message
            if is_token_expired(token):
                logger.warning(f"Expired token used for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": {
                            "code": "TOKEN_EXPIRED",
                            "message": "Your session has expired. Please login again to continue.",
                            "details": {
                                "action": "redirect_to_login",
                                "timestamp": time.time()
                            }
                        }
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Check if token is blacklisted
            if self.blacklist_service.is_token_blacklisted(token):
                logger.warning(f"Blacklisted token used for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": {
                            "code": "TOKEN_REVOKED",
                            "message": "Your session has been revoked. Please login again.",
                            "details": {
                                "action": "redirect_to_login",
                                "timestamp": time.time()
                            }
                        }
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        try:
            response = await call_next(request)
            
            # Log successful authenticated requests
            if auth_header and response.status_code < 400:
                process_time = time.time() - start_time
                logger.info(f"Authenticated request to {request.url.path} completed in {process_time:.3f}s")
            
            return response
            
        except HTTPException as e:
            # Handle authentication-related HTTP exceptions
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.warning(f"Authentication failed for {request.url.path}: {e.detail}")
                return JSONResponse(
                    status_code=e.status_code,
                    content={
                        "error": {
                            "code": "AUTHENTICATION_FAILED",
                            "message": e.detail,
                            "details": {
                                "action": "redirect_to_login",
                                "timestamp": time.time()
                            }
                        }
                    },
                    headers=e.headers or {}
                )
            raise e
        
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware for {request.url.path}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred. Please try again.",
                        "details": {
                            "timestamp": time.time()
                        }
                    }
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for authentication endpoints.
    
    This middleware implements basic rate limiting to prevent brute force attacks
    on authentication endpoints.
    """
    
    def __init__(self, app, max_requests: int = 10, window_seconds: int = 300):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}  # In production, use Redis
        self.rate_limited_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        # Only apply rate limiting to specific paths
        if request.url.path not in self.rate_limited_paths:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        key = f"{client_ip}:{request.url.path}"
        if key in self.request_counts:
            requests, first_request_time = self.request_counts[key]
            
            if current_time - first_request_time < self.window_seconds:
                if requests >= self.max_requests:
                    logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": {
                                "code": "RATE_LIMIT_EXCEEDED",
                                "message": f"Too many requests. Please try again in {self.window_seconds} seconds.",
                                "details": {
                                    "retry_after": self.window_seconds,
                                    "timestamp": current_time
                                }
                            }
                        },
                        headers={"Retry-After": str(self.window_seconds)}
                    )
                else:
                    self.request_counts[key] = (requests + 1, first_request_time)
            else:
                # Reset counter for new window
                self.request_counts[key] = (1, current_time)
        else:
            # First request from this IP for this path
            self.request_counts[key] = (1, current_time)
        
        return await call_next(request)
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old rate limiting entries."""
        keys_to_remove = []
        for key, (_, first_request_time) in self.request_counts.items():
            if current_time - first_request_time >= self.window_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.request_counts[key]