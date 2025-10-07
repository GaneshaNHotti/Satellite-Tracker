"""
Authentication service for user registration and login operations.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse, AuthResponse, RefreshTokenRequest, RefreshTokenResponse
from app.utils.auth import get_password_hash, verify_password, create_access_token, create_refresh_token, extract_user_id_from_token
from app.config import settings


class AuthService:
    """Service class for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: The user's email address
            
        Returns:
            User: The user object if found, None otherwise
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: The user's ID
            
        Returns:
            User: The user object if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user account.
        
        Args:
            user_data: The user registration data
            
        Returns:
            User: The created user object
            
        Raises:
            HTTPException: If email already exists or other database error
        """
        # Check if user already exists
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create new user
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True
        )
        
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: The user's email address
            password: The user's plain text password
            
        Returns:
            User: The authenticated user object if credentials are valid, None otherwise
        """
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    def register_user(self, user_data: UserCreate) -> AuthResponse:
        """
        Register a new user and return authentication response.
        
        Args:
            user_data: The user registration data
            
        Returns:
            AuthResponse: The authentication response with tokens and user data
        """
        # Create the user
        user = self.create_user(user_data)
        
        # Generate access and refresh tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Return authentication response
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(user)
        )
    
    def login_user(self, login_data: UserLogin) -> AuthResponse:
        """
        Login a user and return authentication response.
        
        Args:
            login_data: The user login data
            
        Returns:
            AuthResponse: The authentication response with tokens and user data
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Authenticate user
        user = self.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access and refresh tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Return authentication response
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(user)
        )
    
    def refresh_access_token(self, refresh_request: RefreshTokenRequest) -> RefreshTokenResponse:
        """
        Refresh an access token using a valid refresh token.
        
        Args:
            refresh_request: The refresh token request data
            
        Returns:
            RefreshTokenResponse: New access token
            
        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Extract user ID from refresh token
        user_id = extract_user_id_from_token(refresh_request.refresh_token, token_type="refresh")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = self.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate new access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60  # Convert to seconds
        )