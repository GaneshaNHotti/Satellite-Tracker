"""
Pydantic schemas for the Satellite Tracker API.
"""

from .auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
    AuthResponse
)

from .location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationCoordinates
)

from .favorite import (
    FavoriteCreate,
    FavoriteResponse,
    FavoritesListResponse,
    FavoriteBatchCreate,
    FavoriteBatchResponse,
    FavoriteDeleteResponse,
    FavoritesWithPositionsRequest
)

__all__ = [
    "UserCreate",
    "UserLogin", 
    "UserResponse",
    "Token",
    "TokenData",
    "AuthResponse",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "LocationCoordinates",
    "FavoriteCreate",
    "FavoriteResponse",
    "FavoritesListResponse",
    "FavoriteBatchCreate",
    "FavoriteBatchResponse",
    "FavoriteDeleteResponse",
    "FavoritesWithPositionsRequest"
]