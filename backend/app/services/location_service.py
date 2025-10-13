"""
Location service for managing user location operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from decimal import Decimal

from app.models.location import UserLocation
from app.schemas.location import LocationCreate, LocationUpdate
from app.utils.location import validate_coordinates


class LocationService:
    """Service class for location-related operations."""
    
    @staticmethod
    def create_user_location(
        db: Session, 
        user_id: int, 
        location_data: LocationCreate
    ) -> UserLocation:
        """
        Create a new location for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            location_data: Location creation data
        
        Returns:
            UserLocation: Created location instance
        
        Raises:
            ValueError: If coordinates are invalid
            IntegrityError: If database constraints are violated
        """
        # Validate coordinates
        if not validate_coordinates(float(location_data.latitude), float(location_data.longitude)):
            raise ValueError("Invalid coordinates provided")
        
        # Check if user already has a location (assuming one location per user)
        existing_location = db.query(UserLocation).filter(
            UserLocation.user_id == user_id
        ).first()
        
        if existing_location:
            # Update existing location instead of creating new one
            return LocationService.update_user_location(
                db, user_id, location_data
            )
        
        # Create new location
        db_location = UserLocation(
            user_id=user_id,
            latitude=location_data.latitude,
            longitude=location_data.longitude,
            address=location_data.address
        )
        
        try:
            db.add(db_location)
            db.commit()
            db.refresh(db_location)
            return db_location
        except IntegrityError as e:
            db.rollback()
            raise e
    
    @staticmethod
    def get_user_location(db: Session, user_id: int) -> Optional[UserLocation]:
        """
        Get the current location for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
        
        Returns:
            Optional[UserLocation]: User's location or None if not found
        """
        return db.query(UserLocation).filter(
            UserLocation.user_id == user_id
        ).first()
    
    @staticmethod
    def update_user_location(
        db: Session, 
        user_id: int, 
        location_data: LocationUpdate
    ) -> Optional[UserLocation]:
        """
        Update an existing user location.
        
        Args:
            db: Database session
            user_id: ID of the user
            location_data: Location update data
        
        Returns:
            Optional[UserLocation]: Updated location or None if not found
        
        Raises:
            ValueError: If coordinates are invalid
        """
        # Get existing location
        db_location = db.query(UserLocation).filter(
            UserLocation.user_id == user_id
        ).first()
        
        if not db_location:
            return None
        
        # Update fields if provided
        update_data = location_data.dict(exclude_unset=True)
        
        # Validate coordinates if provided
        if 'latitude' in update_data or 'longitude' in update_data:
            new_lat = update_data.get('latitude', db_location.latitude)
            new_lon = update_data.get('longitude', db_location.longitude)
            
            if not validate_coordinates(float(new_lat), float(new_lon)):
                raise ValueError("Invalid coordinates provided")
        
        # Apply updates
        for field, value in update_data.items():
            setattr(db_location, field, value)
        
        try:
            db.commit()
            db.refresh(db_location)
            return db_location
        except IntegrityError as e:
            db.rollback()
            raise e
    
    @staticmethod
    def delete_user_location(db: Session, user_id: int) -> bool:
        """
        Delete a user's location.
        
        Args:
            db: Database session
            user_id: ID of the user
        
        Returns:
            bool: True if location was deleted, False if not found
        """
        db_location = db.query(UserLocation).filter(
            UserLocation.user_id == user_id
        ).first()
        
        if not db_location:
            return False
        
        db.delete(db_location)
        db.commit()
        return True
    
    @staticmethod
    def get_all_user_locations(db: Session, user_id: int) -> List[UserLocation]:
        """
        Get all locations for a user (in case multiple locations are supported in future).
        
        Args:
            db: Database session
            user_id: ID of the user
        
        Returns:
            List[UserLocation]: List of user locations
        """
        return db.query(UserLocation).filter(
            UserLocation.user_id == user_id
        ).order_by(UserLocation.created_at.desc()).all()
    
    @staticmethod
    def validate_location_data(location_data: LocationCreate) -> List[str]:
        """
        Validate location data and return list of validation errors.
        
        Args:
            location_data: Location data to validate
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        
        try:
            # Validate latitude
            lat = float(location_data.latitude)
            if not -90 <= lat <= 90:
                errors.append("Latitude must be between -90 and 90 degrees")
        except (ValueError, TypeError):
            errors.append("Invalid latitude format")
        
        try:
            # Validate longitude
            lon = float(location_data.longitude)
            if not -180 <= lon <= 180:
                errors.append("Longitude must be between -180 and 180 degrees")
        except (ValueError, TypeError):
            errors.append("Invalid longitude format")
        
        # Validate address if provided
        if location_data.address:
            if len(location_data.address.strip()) > 500:
                errors.append("Address must be 500 characters or less")
        
        return errors