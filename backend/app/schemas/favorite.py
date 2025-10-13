"""
Pydantic schemas for favorite satellites API endpoints.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from app.schemas.satellite import SatelliteInfo, SatellitePosition


class FavoriteCreate(BaseModel):
    """Schema for creating a favorite satellite."""
    norad_id: int = Field(..., description="NORAD catalog number of the satellite to add to favorites")
    
    @validator('norad_id')
    def validate_norad_id(cls, v):
        if not (1 <= v <= 999999):
            raise ValueError('NORAD ID must be between 1 and 999999')
        return v


class FavoriteResponse(BaseModel):
    """Schema for favorite satellite response."""
    id: int = Field(..., description="Unique favorite ID")
    norad_id: int = Field(..., description="NORAD catalog number")
    name: str = Field(..., description="Satellite name")
    category: Optional[str] = Field(None, description="Satellite category")
    added_at: datetime = Field(..., description="When the satellite was added to favorites")
    current_position: Optional[SatellitePosition] = Field(None, description="Current position data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FavoritesListResponse(BaseModel):
    """Schema for favorites list response."""
    favorites: List[FavoriteResponse] = Field(..., description="List of favorite satellites")
    total: int = Field(..., description="Total number of favorites")
    
    
class FavoriteBatchCreate(BaseModel):
    """Schema for batch creating favorite satellites."""
    norad_ids: List[int] = Field(..., min_items=1, max_items=50, description="List of NORAD IDs to add to favorites")
    
    @validator('norad_ids')
    def validate_norad_ids(cls, v):
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('Duplicate NORAD IDs are not allowed')
        
        # Validate each NORAD ID
        for norad_id in v:
            if not (1 <= norad_id <= 999999):
                raise ValueError(f'Invalid NORAD ID: {norad_id}. Must be between 1 and 999999')
        
        return v


class FavoriteBatchResponse(BaseModel):
    """Schema for batch operation response."""
    added: List[FavoriteResponse] = Field(..., description="Successfully added favorites")
    skipped: List[dict] = Field(..., description="Skipped items with reasons")
    total_added: int = Field(..., description="Number of favorites added")
    total_skipped: int = Field(..., description="Number of items skipped")


class FavoriteDeleteResponse(BaseModel):
    """Schema for favorite deletion response."""
    message: str = Field(..., description="Deletion confirmation message")
    deleted_favorite: dict = Field(..., description="Information about the deleted favorite")


class FavoritesWithPositionsRequest(BaseModel):
    """Schema for requesting favorites with current positions."""
    include_positions: bool = Field(True, description="Whether to include current position data")
    use_cache: bool = Field(True, description="Whether to use cached position data")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: dict = Field(..., description="Error information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "DUPLICATE_FAVORITE",
                    "message": "Satellite is already in favorites",
                    "details": {
                        "norad_id": 25544,
                        "existing_favorite_id": 123
                    },
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    }