"""
FastAPI dependencies for authentication and database access.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.token_blacklist_service import TokenBlacklistService
from app.utils.auth import extract_user_id_from_token

# HTTP Bearer token scheme
security = HTTPBearer()


def get_token_blacklist_service() -> TokenBlacklistService:
    """
    Get token blacklist service instance.
    
    Returns:
        TokenBlacklistService: The token blacklist service instance
    """
    return TokenBlacklistService()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Get authentication service instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthService: The authentication service instance
    """
    return AuthService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        auth_service: Authentication service instance
        blacklist_service: Token blacklist service instance
        
    Returns:
        User: The current authenticated user
        
    Raises:
        HTTPException: If token is invalid, blacklisted, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Check if token is blacklisted
    if blacklist_service.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID from token
    user_id = extract_user_id_from_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        User: The current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.
    This is useful for endpoints that work for both authenticated and anonymous users.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        auth_service: Authentication service instance
        blacklist_service: Token blacklist service instance
        
    Returns:
        User: The current authenticated user or None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted
        if blacklist_service.is_token_blacklisted(token):
            return None
        
        user_id = extract_user_id_from_token(token)
        if user_id is None:
            return None
        
        user = auth_service.get_user_by_id(user_id)
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception:
        return None