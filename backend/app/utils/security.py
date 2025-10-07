"""
Security utilities for the application.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Utility class for security-related operations."""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of the token in bytes
            
        Returns:
            str: Hex-encoded secure token
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_csrf_token() -> str:
        """
        Generate a CSRF token.
        
        Returns:
            str: CSRF token
        """
        return SecurityUtils.generate_secure_token(16)
    
    @staticmethod
    def verify_csrf_token(token: str, expected_token: str) -> bool:
        """
        Verify a CSRF token using constant-time comparison.
        
        Args:
            token: The token to verify
            expected_token: The expected token value
            
        Returns:
            bool: True if tokens match
        """
        return secrets.compare_digest(token, expected_token)
    
    @staticmethod
    def create_signature(data: str, secret: str) -> str:
        """
        Create an HMAC signature for data.
        
        Args:
            data: The data to sign
            secret: The secret key
            
        Returns:
            str: Hex-encoded signature
        """
        return hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_signature(data: str, signature: str, secret: str) -> bool:
        """
        Verify an HMAC signature.
        
        Args:
            data: The original data
            signature: The signature to verify
            secret: The secret key
            
        Returns:
            bool: True if signature is valid
        """
        expected_signature = SecurityUtils.create_signature(data, secret)
        return secrets.compare_digest(signature, expected_signature)
    
    @staticmethod
    def sanitize_user_input(input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize user input by removing potentially dangerous characters.
        
        Args:
            input_str: The input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            str: Sanitized string
            
        Raises:
            HTTPException: If input is too long
        """
        if len(input_str) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input too long. Maximum length is {max_length} characters."
            )
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
        
        return sanitized.strip()
    
    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
        """
        Check if a redirect URL is safe (prevents open redirect attacks).
        
        Args:
            url: The URL to check
            allowed_hosts: List of allowed hosts
            
        Returns:
            bool: True if URL is safe for redirect
        """
        if not url:
            return False
        
        # Only allow relative URLs or URLs from allowed hosts
        if url.startswith('/'):
            return True
        
        if allowed_hosts:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc in allowed_hosts
        
        return False


class SessionSecurity:
    """Security utilities for session management."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """
        Create a new session with security metadata.
        
        Args:
            user_id: The user ID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            str: Session ID
        """
        session_id = SecurityUtils.generate_secure_token()
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_active": True
        }
        
        return session_id
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> bool:
        """
        Validate a session with security checks.
        
        Args:
            session_id: The session ID to validate
            ip_address: Current client IP address
            user_agent: Current client user agent
            
        Returns:
            bool: True if session is valid
        """
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Check if session is active
        if not session.get("is_active", False):
            return False
        
        # Check for session hijacking (IP address change)
        if session["ip_address"] != ip_address:
            logger.warning(f"Session {session_id} IP address mismatch: {session['ip_address']} vs {ip_address}")
            self.invalidate_session(session_id)
            return False
        
        # Check for session hijacking (user agent change)
        if session["user_agent"] != user_agent:
            logger.warning(f"Session {session_id} user agent mismatch")
            self.invalidate_session(session_id)
            return False
        
        # Check session timeout (24 hours)
        if datetime.utcnow() - session["last_activity"] > timedelta(hours=24):
            logger.info(f"Session {session_id} expired due to inactivity")
            self.invalidate_session(session_id)
            return False
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return True
    
    def invalidate_session(self, session_id: str):
        """
        Invalidate a session.
        
        Args:
            session_id: The session ID to invalidate
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_active"] = False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session["last_activity"] > timedelta(hours=24):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Global session security instance
session_security = SessionSecurity()