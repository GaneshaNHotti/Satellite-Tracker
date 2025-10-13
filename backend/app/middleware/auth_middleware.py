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
    Enhanced rate limiting middleware with multiple strategies.
    
    This middleware implements rate limiting to prevent abuse and brute force attacks
    with different limits for different endpoint types.
    """
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        self.request_counts = {}  # Fallback when Redis is not available
        
        # Rate limiting configurations for different endpoint types
        self.rate_limits = {
            "auth": {
                "paths": ["/api/v1/auth/login", "/api/v1/auth/register"],
                "max_requests": 5,
                "window_seconds": 300,  # 5 minutes
                "block_duration": 900   # 15 minutes
            },
            "api": {
                "paths": ["/api/v1/"],  # All API endpoints
                "max_requests": 100,
                "window_seconds": 60,   # 1 minute
                "block_duration": 300   # 5 minutes
            },
            "search": {
                "paths": ["/api/v1/satellites/search"],
                "max_requests": 20,
                "window_seconds": 60,   # 1 minute
                "block_duration": 180   # 3 minutes
            }
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply appropriate rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or endpoint
        """
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Determine which rate limit to apply
        rate_limit_config = self._get_rate_limit_config(request.url.path)
        if not rate_limit_config:
            return await call_next(request)
        
        # Check if client is currently blocked
        if await self._is_client_blocked(client_ip, rate_limit_config, current_time):
            logger.warning(
                f"Blocked client {client_ip} attempted access to {request.url.path}",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "rate_limit_type": rate_limit_config["type"]
                }
            )
            return self._create_rate_limit_response(rate_limit_config["block_duration"])
        
        # Check current rate limit
        if await self._check_rate_limit(client_ip, request.url.path, rate_limit_config, current_time):
            # Rate limit exceeded - block the client
            await self._block_client(client_ip, rate_limit_config, current_time)
            
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path}",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "rate_limit_type": rate_limit_config["type"],
                    "max_requests": rate_limit_config["max_requests"],
                    "window_seconds": rate_limit_config["window_seconds"]
                }
            )
            return self._create_rate_limit_response(rate_limit_config["block_duration"])
        
        # Record the request
        await self._record_request(client_ip, request.url.path, rate_limit_config, current_time)
        
        return await call_next(request)
    
    def _get_rate_limit_config(self, path: str) -> dict:
        """
        Get the appropriate rate limit configuration for the given path.
        
        Args:
            path: Request path
            
        Returns:
            Rate limit configuration or None if no limits apply
        """
        # Check specific paths first (most restrictive)
        for limit_type, config in self.rate_limits.items():
            for limit_path in config["paths"]:
                if path == limit_path or (limit_path.endswith("/") and path.startswith(limit_path)):
                    return {**config, "type": limit_type}
        
        return None
    
    async def _is_client_blocked(self, client_ip: str, config: dict, current_time: float) -> bool:
        """
        Check if a client is currently blocked.
        
        Args:
            client_ip: Client IP address
            config: Rate limit configuration
            current_time: Current timestamp
            
        Returns:
            True if client is blocked, False otherwise
        """
        block_key = f"blocked:{config['type']}:{client_ip}"
        
        if self.redis_client:
            try:
                blocked_until = await self.redis_client.get(block_key)
                if blocked_until and float(blocked_until) > current_time:
                    return True
            except Exception as e:
                logger.error(f"Redis error checking block status: {e}")
        else:
            # Fallback to in-memory storage
            if block_key in self.request_counts:
                blocked_until = self.request_counts[block_key]
                if blocked_until > current_time:
                    return True
                else:
                    del self.request_counts[block_key]
        
        return False
    
    async def _check_rate_limit(self, client_ip: str, path: str, config: dict, current_time: float) -> bool:
        """
        Check if the rate limit has been exceeded.
        
        Args:
            client_ip: Client IP address
            path: Request path
            config: Rate limit configuration
            current_time: Current timestamp
            
        Returns:
            True if rate limit exceeded, False otherwise
        """
        rate_key = f"rate:{config['type']}:{client_ip}"
        
        if self.redis_client:
            try:
                # Use Redis sliding window
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(rate_key, 0, current_time - config["window_seconds"])
                pipe.zcard(rate_key)
                pipe.zadd(rate_key, {str(current_time): current_time})
                pipe.expire(rate_key, config["window_seconds"])
                results = await pipe.execute()
                
                request_count = results[1]
                return request_count >= config["max_requests"]
                
            except Exception as e:
                logger.error(f"Redis error checking rate limit: {e}")
                # Fall back to in-memory check
        
        # Fallback to in-memory storage
        if rate_key not in self.request_counts:
            self.request_counts[rate_key] = []
        
        # Clean old entries
        self.request_counts[rate_key] = [
            timestamp for timestamp in self.request_counts[rate_key]
            if current_time - timestamp < config["window_seconds"]
        ]
        
        # Check if limit exceeded
        if len(self.request_counts[rate_key]) >= config["max_requests"]:
            return True
        
        return False
    
    async def _record_request(self, client_ip: str, path: str, config: dict, current_time: float):
        """
        Record a request for rate limiting purposes.
        
        Args:
            client_ip: Client IP address
            path: Request path
            config: Rate limit configuration
            current_time: Current timestamp
        """
        rate_key = f"rate:{config['type']}:{client_ip}"
        
        if not self.redis_client:
            # Add to in-memory storage
            if rate_key not in self.request_counts:
                self.request_counts[rate_key] = []
            self.request_counts[rate_key].append(current_time)
    
    async def _block_client(self, client_ip: str, config: dict, current_time: float):
        """
        Block a client for the specified duration.
        
        Args:
            client_ip: Client IP address
            config: Rate limit configuration
            current_time: Current timestamp
        """
        block_key = f"blocked:{config['type']}:{client_ip}"
        blocked_until = current_time + config["block_duration"]
        
        if self.redis_client:
            try:
                await self.redis_client.setex(block_key, config["block_duration"], str(blocked_until))
            except Exception as e:
                logger.error(f"Redis error blocking client: {e}")
        else:
            # Fallback to in-memory storage
            self.request_counts[block_key] = blocked_until
    
    def _create_rate_limit_response(self, retry_after: int) -> JSONResponse:
        """
        Create a rate limit exceeded response.
        
        Args:
            retry_after: Seconds to wait before retrying
            
        Returns:
            JSONResponse with rate limit error
        """
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "details": {
                        "retry_after": retry_after,
                        "timestamp": time.time()
                    }
                }
            },
            headers={"Retry-After": str(retry_after)}
        )