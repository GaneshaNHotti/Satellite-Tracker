"""
Pydantic schemas for location-related operations.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional


class LocationCreate(BaseModel):
    """Schema for creating a new user location."""
    latitude: Decimal = Field(..., description="Latitude coordinate", ge=-90, le=90)
    longitude: Decimal = Field(..., description="Longitude coordinate", ge=-180, le=180)
    address: Optional[str] = Field(None, description="Optional address description", max_length=500)
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        """Validate latitude is within valid range."""
        if v is None:
            raise ValueError('Latitude is required')
        lat_float = float(v)
        if not -90 <= lat_float <= 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        """Validate longitude is within valid range."""
        if v is None:
            raise ValueError('Longitude is required')
        lon_float = float(v)
        if not -180 <= lon_float <= 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        """Validate address if provided."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 500:
                raise ValueError('Address must be 500 characters or less')
        return v


class LocationUpdate(BaseModel):
    """Schema for updating an existing user location."""
    latitude: Optional[Decimal] = Field(None, description="Latitude coordinate", ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, description="Longitude coordinate", ge=-180, le=180)
    address: Optional[str] = Field(None, description="Optional address description", max_length=500)
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        """Validate latitude is within valid range."""
        if v is not None:
            lat_float = float(v)
            if not -90 <= lat_float <= 90:
                raise ValueError('Latitude must be between -90 and 90 degrees')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        """Validate longitude is within valid range."""
        if v is not None:
            lon_float = float(v)
            if not -180 <= lon_float <= 180:
                raise ValueError('Longitude must be between -180 and 180 degrees')
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        """Validate address if provided."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 500:
                raise ValueError('Address must be 500 characters or less')
        return v


class LocationResponse(BaseModel):
    """Schema for location response data."""
    id: int
    latitude: Decimal
    longitude: Decimal
    address: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LocationCoordinates(BaseModel):
    """Schema for simple coordinate pair."""
    latitude: Decimal = Field(..., description="Latitude coordinate", ge=-90, le=90)
    longitude: Decimal = Field(..., description="Longitude coordinate", ge=-180, le=180)
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        """Validate latitude is within valid range."""
        lat_float = float(v)
        if not -90 <= lat_float <= 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        """Validate longitude is within valid range."""
        lon_float = float(v)
        if not -180 <= lon_float <= 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')
        return v