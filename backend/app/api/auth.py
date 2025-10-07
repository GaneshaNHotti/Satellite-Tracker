"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import UserCreate, UserLogin, AuthResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.token_blacklist_service import TokenBlacklistService
from app.utils.dependencies import get_current_active_user, get_token_blacklist_service
from app.models.user import User

# HTTP Bearer token scheme for logout
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Args:
        user_data: User registration data (email, password, confirm_password)
        db: Database session
        
    Returns:
        AuthResponse: JWT token and user information
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)


@router.post("/login", response_model=AuthResponse)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Args:
        login_data: User login credentials (email, password)
        db: Database session
        
    Returns:
        AuthResponse: JWT token and user information
        
    Raises:
        HTTPException: If credentials are invalid
    """
    auth_service = AuthService(db)
    return auth_service.login_user(login_data)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
):
    """
    Logout user by blacklisting the JWT token.
    
    Args:
        credentials: HTTP authorization credentials containing the JWT token
        blacklist_service: Token blacklist service instance
    
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If token is invalid or blacklisting fails
    """
    token = credentials.credentials
    
    # Blacklist the token
    success = blacklist_service.blacklist_token(token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout. Invalid token."
        )
    
    return {"message": "Successfully logged out"}