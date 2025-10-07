"""
Token blacklist service for handling JWT token invalidation.
"""

from typing import Optional, Dict, Set
from datetime import datetime, timedelta
import redis
from app.config import settings
from app.utils.auth import verify_token

class TokenBlacklistService:
    """Service for managing blacklisted JWT tokens."""
    
    def __init__(self):
        """Initialize Redis connection for token blacklist with fallback to in-memory store."""
        self.redis_client = None
        self.in_memory_blacklist: Dict[str, datetime] = {}  # Fallback storage
        
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            print("Connected to Redis for token blacklisting")
        except Exception as e:
            print(f"Redis connection failed, using in-memory blacklist: {e}")
            self.redis_client = None
    
    def blacklist_token(self, token: str) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token: The JWT token to blacklist
            
        Returns:
            bool: True if token was successfully blacklisted
        """
        try:
            # Verify token and get expiration
            payload = verify_token(token)
            if not payload:
                return False
            
            # Get token expiration time
            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                return False
            
            # Calculate expiration datetime
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            current_time = datetime.utcnow()
            
            if exp_datetime <= current_time:
                # Token already expired, no need to blacklist
                return True
            
            if self.redis_client:
                # Use Redis if available
                ttl_seconds = int((exp_datetime - current_time).total_seconds())
                key = f"blacklisted_token:{token}"
                self.redis_client.setex(key, ttl_seconds, "blacklisted")
            else:
                # Use in-memory storage as fallback
                self.in_memory_blacklist[token] = exp_datetime
                # Clean up expired tokens
                self._cleanup_expired_memory_tokens()
            
            return True
            
        except Exception as e:
            print(f"Error blacklisting token: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token: The JWT token to check
            
        Returns:
            bool: True if token is blacklisted
        """
        try:
            if self.redis_client:
                # Use Redis if available
                key = f"blacklisted_token:{token}"
                return self.redis_client.exists(key) > 0
            else:
                # Use in-memory storage as fallback
                if token in self.in_memory_blacklist:
                    # Check if token has expired
                    exp_time = self.in_memory_blacklist[token]
                    if datetime.utcnow() >= exp_time:
                        # Token expired, remove from blacklist
                        del self.in_memory_blacklist[token]
                        return False
                    return True
                return False
        except Exception as e:
            print(f"Error checking token blacklist: {e}")
            # If there's an error, allow the request (fail open)
            return False
    
    def _cleanup_expired_memory_tokens(self):
        """Clean up expired tokens from in-memory storage."""
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, exp_time in self.in_memory_blacklist.items()
            if current_time >= exp_time
        ]
        for token in expired_tokens:
            del self.in_memory_blacklist[token]
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from blacklist.
        
        Returns:
            int: Number of tokens cleaned up
        """
        try:
            if self.redis_client:
                # Get all blacklisted token keys
                keys = self.redis_client.keys("blacklisted_token:*")
                
                # Redis TTL automatically removes expired keys,
                # but we can manually check and remove if needed
                cleaned_count = 0
                for key in keys:
                    ttl = self.redis_client.ttl(key)
                    if ttl == -2:  # Key doesn't exist (expired)
                        cleaned_count += 1
                
                return cleaned_count
            else:
                # Clean up in-memory storage
                initial_count = len(self.in_memory_blacklist)
                self._cleanup_expired_memory_tokens()
                return initial_count - len(self.in_memory_blacklist)
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0