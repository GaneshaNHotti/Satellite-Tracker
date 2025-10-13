"""
Location API endpoints for user location management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.services.location_service import LocationService
from app.utils.dependencies import get_db, get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["locations"])


@router.post(
    "/location",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update user location",
    description="Save the user's geographical location (latitude and longitude) with optional address information."
)
async def create_user_location(
    location_data: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update a user's location.
    
    - **latitude**: Latitude coordinate (-90 to 90 degrees)
    - **longitude**: Longitude coordinate (-180 to 180 degrees)  
    - **address**: Optional address description (max 500 characters)
    
    If the user already has a location, it will be updated with the new data.
    """
    try:
        location = LocationService.create_user_location(
            db=db,
            user_id=current_user.id,
            location_data=location_data
        )
        return location
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save location"
        )


@router.get(
    "/location",
    response_model=LocationResponse,
    summary="Get user location",
    description="Retrieve the user's saved geographical location."
)
async def get_user_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's saved location.
    
    Returns the user's latitude, longitude, and optional address information.
    """
    location = LocationService.get_user_location(db=db, user_id=current_user.id)
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User location not found. Please set your location first."
        )
    
    return location


@router.put(
    "/location",
    response_model=LocationResponse,
    summary="Update user location",
    description="Update the user's existing location with new coordinates or address."
)
async def update_user_location(
    location_data: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the user's existing location.
    
    - **latitude**: New latitude coordinate (optional)
    - **longitude**: New longitude coordinate (optional)
    - **address**: New address description (optional)
    
    Only provided fields will be updated. At least one field must be provided.
    """
    # Check if any fields are provided for update
    update_data = location_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update"
        )
    
    try:
        location = LocationService.update_user_location(
            db=db,
            user_id=current_user.id,
            location_data=location_data
        )
        
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User location not found. Please create a location first."
            )
        
        return location
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update location"
        )


@router.delete(
    "/location",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user location",
    description="Delete the user's saved location."
)
async def delete_user_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the user's saved location.
    
    This will remove all location data for the user.
    """
    success = LocationService.delete_user_location(db=db, user_id=current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User location not found"
        )


@router.get(
    "/location/validate",
    summary="Validate coordinates",
    description="Validate latitude and longitude coordinates without saving them."
)
async def validate_coordinates(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user)
):
    """
    Validate coordinate values.
    
    - **latitude**: Latitude coordinate to validate
    - **longitude**: Longitude coordinate to validate
    
    Returns validation result and any error messages.
    """
    from app.utils.location import validate_coordinates
    
    is_valid = validate_coordinates(latitude, longitude)
    
    errors = []
    if not is_valid:
        if not -90 <= latitude <= 90:
            errors.append("Latitude must be between -90 and 90 degrees")
        if not -180 <= longitude <= 180:
            errors.append("Longitude must be between -180 and 180 degrees")
    
    return {
        "valid": is_valid,
        "latitude": latitude,
        "longitude": longitude,
        "errors": errors
    }