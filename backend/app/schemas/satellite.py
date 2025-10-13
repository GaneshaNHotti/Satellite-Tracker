"""
Pydantic schemas for satellite-related API endpoints.
"""

from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class SatellitePosition(BaseModel):
    """Schema for satellite position data."""
    latitude: Decimal = Field(..., description="Satellite latitude in degrees")
    longitude: Decimal = Field(..., description="Satellite longitude in degrees")
    altitude: Decimal = Field(..., description="Satellite altitude in kilometers")
    velocity: Decimal = Field(..., description="Satellite velocity in km/s")
    timestamp: datetime = Field(..., description="Timestamp of the position data")
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class SatelliteInfo(BaseModel):
    """Schema for satellite information."""
    norad_id: int = Field(..., description="NORAD catalog number")
    name: str = Field(..., description="Satellite name")
    launch_date: Optional[str] = Field(None, description="Launch date (YYYY-MM-DD)")
    country: Optional[str] = Field(None, description="Country of origin")
    category: Optional[str] = Field(None, description="Satellite category")
    current_position: Optional[SatellitePosition] = Field(None, description="Current position data")
    
    @validator('norad_id')
    def validate_norad_id(cls, v):
        if not (1 <= v <= 999999):
            raise ValueError('NORAD ID must be between 1 and 999999')
        return v


class SatelliteSearchResponse(BaseModel):
    """Schema for satellite search response."""
    satellites: List[SatelliteInfo] = Field(..., description="List of matching satellites")
    total: int = Field(..., description="Total number of satellites found")
    query: str = Field(..., description="Search query used")


class SatelliteSearchRequest(BaseModel):
    """Schema for satellite search request."""
    query: str = Field(..., min_length=2, max_length=100, description="Search query (satellite name)")
    category: Optional[str] = Field(None, description="Filter by category")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class SatellitePass(BaseModel):
    """Schema for satellite pass prediction."""
    start_time: datetime = Field(..., description="Pass start time (UTC)")
    end_time: datetime = Field(..., description="Pass end time (UTC)")
    duration: int = Field(..., description="Pass duration in seconds")
    max_elevation: Decimal = Field(..., description="Maximum elevation angle in degrees")
    start_azimuth: Optional[Decimal] = Field(None, description="Starting azimuth in degrees")
    end_azimuth: Optional[Decimal] = Field(None, description="Ending azimuth in degrees")
    magnitude: Optional[Decimal] = Field(None, description="Visual magnitude (brightness)")
    visibility: str = Field(..., description="Visibility status (visible/not_visible)")
    is_visible: Optional[bool] = Field(None, description="Whether the pass is visible to naked eye")
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }


class SatellitePassesResponse(BaseModel):
    """Schema for satellite passes response."""
    satellite: SatelliteInfo = Field(..., description="Satellite information")
    location: dict = Field(..., description="Observer location")
    passes: List[SatellitePass] = Field(..., description="List of upcoming passes")
    total: int = Field(..., description="Total number of passes")
    days_predicted: int = Field(..., description="Number of days predicted")


class SatellitePositionRequest(BaseModel):
    """Schema for satellite position request."""
    latitude: Decimal = Field(..., ge=-90, le=90, description="Observer latitude in degrees")
    longitude: Decimal = Field(..., ge=-180, le=180, description="Observer longitude in degrees")
    altitude: Decimal = Field(0, ge=0, le=10000, description="Observer altitude in meters")
    
    class Config:
        json_encoders = {
            Decimal: float
        }


class SatellitePassesRequest(BaseModel):
    """Schema for satellite passes request."""
    latitude: Decimal = Field(..., ge=-90, le=90, description="Observer latitude in degrees")
    longitude: Decimal = Field(..., ge=-180, le=180, description="Observer longitude in degrees")
    altitude: Decimal = Field(0, ge=0, le=10000, description="Observer altitude in meters")
    days: int = Field(10, ge=1, le=10, description="Number of days to predict")
    min_elevation: Decimal = Field(0, ge=0, le=90, description="Minimum elevation for visible passes")
    
    class Config:
        json_encoders = {
            Decimal: float
        }


class APIRateLimitStatus(BaseModel):
    """Schema for API rate limit status."""
    requests_remaining: Optional[int] = Field(None, description="Number of requests remaining")
    reset_time: Optional[str] = Field(None, description="Time when rate limit resets (ISO format)")
    api_name: str = Field("N2YO", description="Name of the external API")


class CacheStatus(BaseModel):
    """Schema for cache status information."""
    positions_cached: int = Field(..., description="Number of position entries in cache")
    passes_cached: int = Field(..., description="Number of pass entries in cache")
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate percentage")
    last_cleanup: Optional[datetime] = Field(None, description="Last cache cleanup time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: dict = Field(..., description="Error information")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {
                        "field": "norad_id",
                        "issue": "NORAD ID must be between 1 and 999999"
                    },
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }