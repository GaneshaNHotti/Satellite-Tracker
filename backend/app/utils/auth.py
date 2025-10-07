"""
Authentication utilities for password hashing and JWT token management.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
import bcrypt
from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at time
        "type": "access"  # Token type
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: The encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Refresh tokens last longer (7 days by default)
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at time
        "type": "refresh"  # Token type
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        dict: The decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            return None
            
        return payload
    except JWTError:
        return None


def extract_user_id_from_token(token: str, token_type: str = "access") -> Optional[int]:
    """
    Extract user ID from a JWT token.
    
    Args:
        token: The JWT token
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        int: The user ID if token is valid, None otherwise
    """
    payload = verify_token(token, token_type)
    if payload:
        user_id: Union[str, int] = payload.get("sub")
        if user_id:
            try:
                return int(user_id)
            except (ValueError, TypeError):
                return None
    return None


def is_token_expired(token: str) -> bool:
    """
    Check if a JWT token is expired.
    
    Args:
        token: The JWT token to check
        
    Returns:
        bool: True if token is expired, False otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            return datetime.utcnow() >= exp_datetime
        return True  # No expiration means invalid token
    except JWTError:
        return True  # Invalid token is considered expired