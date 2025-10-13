"""
Favorite satellites service for managing user's favorite satellite list.
Provides operations for adding, removing, and retrieving favorite satellites with position data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import Depends

from app.database import get_db
from app.models.favorite import UserFavoriteSatellite
from app.models.satellite import Satellite
from app.models.user import User
from app.services.satellite_service import SatelliteService
from app.utils.exceptions import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    ExternalAPIError
)

logger = logging.getLogger(__name__)


class FavoriteService:
    """
    Service for managing user's favorite satellites.
    Handles adding, removing, and retrieving favorites with satellite details and positions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.satellite_service = SatelliteService(db)
    
    async def add_favorite(self, user_id: int, norad_id: int) -> Dict[str, Any]:
        """
        Add a satellite to user's favorites list.
        
        Args:
            user_id: ID of the user
            norad_id: NORAD ID of the satellite to add
            
        Returns:
            Dictionary containing favorite information
            
        Raises:
            ValidationError: If NORAD ID is invalid
            NotFoundError: If user or satellite not found
            ConflictError: If satellite is already in favorites
        """
        # Validate NORAD ID
        if not (1 <= norad_id <= 999999):
            raise ValidationError(f"Invalid NORAD ID: {norad_id}", field="norad_id")
        
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found", resource_type="user", resource_id=str(user_id))
        
        # Check if satellite is already in favorites
        existing_favorite = self.db.query(UserFavoriteSatellite).filter(
            UserFavoriteSatellite.user_id == user_id,
            UserFavoriteSatellite.norad_id == norad_id
        ).first()
        
        if existing_favorite:
            raise ConflictError(
                f"Satellite {norad_id} is already in favorites",
                resource_type="favorite",
                details={"norad_id": norad_id, "existing_favorite_id": existing_favorite.id}
            )
        
        # Get or create satellite information
        try:
            satellite_info = await self.satellite_service.get_satellite_info(norad_id)
        except (ExternalAPIError, NotFoundError):
            # If we can't get satellite info from API, create a basic entry
            satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
            if not satellite:
                satellite = Satellite(
                    norad_id=norad_id,
                    name=f"Satellite {norad_id}",
                    category="Unknown"
                )
                self.db.add(satellite)
                try:
                    self.db.commit()
                except IntegrityError:
                    self.db.rollback()
                    # Satellite might have been created by another request
                    satellite = self.db.query(Satellite).filter(Satellite.norad_id == norad_id).first()
        
        # Create favorite entry
        favorite = UserFavoriteSatellite(
            user_id=user_id,
            norad_id=norad_id
        )
        
        self.db.add(favorite)
        
        try:
            self.db.commit()
            self.db.refresh(favorite)
            
            # Load the satellite relationship
            favorite = self.db.query(UserFavoriteSatellite).options(
                joinedload(UserFavoriteSatellite.satellite)
            ).filter(UserFavoriteSatellite.id == favorite.id).first()
            
            logger.info(f"Added satellite {norad_id} to favorites for user {user_id}")
            
            return {
                "id": favorite.id,
                "norad_id": favorite.norad_id,
                "name": favorite.satellite.name if favorite.satellite else f"Satellite {norad_id}",
                "category": favorite.satellite.category if favorite.satellite else "Unknown",
                "added_at": favorite.created_at
            }
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database error adding favorite {norad_id} for user {user_id}: {e}")
            raise ConflictError(
                f"Satellite {norad_id} is already in favorites",
                resource_type="favorite",
                details={"norad_id": norad_id}
            )
    
    def remove_favorite(self, user_id: int, favorite_id: int) -> Dict[str, Any]:
        """
        Remove a satellite from user's favorites list.
        
        Args:
            user_id: ID of the user
            favorite_id: ID of the favorite to remove
            
        Returns:
            Dictionary containing removal confirmation
            
        Raises:
            NotFoundError: If favorite not found or doesn't belong to user
        """
        # Find the favorite
        favorite = self.db.query(UserFavoriteSatellite).options(
            joinedload(UserFavoriteSatellite.satellite)
        ).filter(
            UserFavoriteSatellite.id == favorite_id,
            UserFavoriteSatellite.user_id == user_id
        ).first()
        
        if not favorite:
            raise NotFoundError(
                f"Favorite {favorite_id} not found for user {user_id}",
                resource_type="favorite",
                resource_id=str(favorite_id)
            )
        
        # Store favorite info before deletion
        favorite_info = {
            "id": favorite.id,
            "norad_id": favorite.norad_id,
            "name": favorite.satellite.name if favorite.satellite else f"Satellite {favorite.norad_id}",
            "added_at": favorite.created_at
        }
        
        # Delete the favorite
        self.db.delete(favorite)
        self.db.commit()
        
        logger.info(f"Removed favorite {favorite_id} (satellite {favorite.norad_id}) for user {user_id}")
        
        return {
            "message": f"Satellite {favorite.norad_id} removed from favorites",
            "deleted_favorite": favorite_info
        }
    
    def remove_favorite_by_norad_id(self, user_id: int, norad_id: int) -> Dict[str, Any]:
        """
        Remove a satellite from user's favorites list by NORAD ID.
        
        Args:
            user_id: ID of the user
            norad_id: NORAD ID of the satellite to remove
            
        Returns:
            Dictionary containing removal confirmation
            
        Raises:
            NotFoundError: If favorite not found
        """
        # Find the favorite
        favorite = self.db.query(UserFavoriteSatellite).options(
            joinedload(UserFavoriteSatellite.satellite)
        ).filter(
            UserFavoriteSatellite.user_id == user_id,
            UserFavoriteSatellite.norad_id == norad_id
        ).first()
        
        if not favorite:
            raise NotFoundError(
                f"Satellite {norad_id} not found in favorites for user {user_id}",
                resource_type="favorite",
                resource_id=str(norad_id)
            )
        
        return self.remove_favorite(user_id, favorite.id)
    
    async def get_user_favorites(self, user_id: int, include_positions: bool = True, 
                               use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all favorite satellites for a user with optional position data.
        
        Args:
            user_id: ID of the user
            include_positions: Whether to include current position data
            use_cache: Whether to use cached position data
            
        Returns:
            List of favorite satellite dictionaries with position data
            
        Raises:
            NotFoundError: If user not found
        """
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found", resource_type="user", resource_id=str(user_id))
        
        # Get user's favorites with satellite information
        favorites = self.db.query(UserFavoriteSatellite).options(
            joinedload(UserFavoriteSatellite.satellite)
        ).filter(
            UserFavoriteSatellite.user_id == user_id
        ).order_by(UserFavoriteSatellite.created_at.desc()).all()
        
        result = []
        
        for favorite in favorites:
            favorite_data = {
                "id": favorite.id,
                "norad_id": favorite.norad_id,
                "name": favorite.satellite.name if favorite.satellite else f"Satellite {favorite.norad_id}",
                "category": favorite.satellite.category if favorite.satellite else "Unknown",
                "added_at": favorite.created_at,
                "current_position": None
            }
            
            # Add position data if requested
            if include_positions and user.locations:
                # Use the user's most recent location
                location = user.locations[-1]  # Assuming locations are ordered by creation
                try:
                    position_data = await self.satellite_service.get_satellite_position(
                        favorite.norad_id,
                        float(location.latitude),
                        float(location.longitude),
                        0,  # altitude
                        use_cache
                    )
                    favorite_data["current_position"] = position_data
                except Exception as e:
                    logger.warning(f"Failed to get position for satellite {favorite.norad_id}: {e}")
                    # Continue without position data
            
            result.append(favorite_data)
        
        logger.info(f"Retrieved {len(result)} favorites for user {user_id}")
        return result
    
    async def add_multiple_favorites(self, user_id: int, norad_ids: List[int]) -> Dict[str, Any]:
        """
        Add multiple satellites to user's favorites list.
        
        Args:
            user_id: ID of the user
            norad_ids: List of NORAD IDs to add
            
        Returns:
            Dictionary containing batch operation results
        """
        added = []
        skipped = []
        
        for norad_id in norad_ids:
            try:
                favorite_data = await self.add_favorite(user_id, norad_id)
                added.append(favorite_data)
            except ConflictError:
                skipped.append({
                    "norad_id": norad_id,
                    "reason": "Already in favorites"
                })
            except ValidationError as e:
                skipped.append({
                    "norad_id": norad_id,
                    "reason": f"Invalid NORAD ID: {e.message}"
                })
            except Exception as e:
                logger.error(f"Unexpected error adding favorite {norad_id}: {e}")
                skipped.append({
                    "norad_id": norad_id,
                    "reason": "Internal error"
                })
        
        logger.info(f"Batch add favorites for user {user_id}: {len(added)} added, {len(skipped)} skipped")
        
        return {
            "added": added,
            "skipped": skipped,
            "total_added": len(added),
            "total_skipped": len(skipped)
        }
    
    def get_favorite_by_id(self, user_id: int, favorite_id: int) -> Dict[str, Any]:
        """
        Get a specific favorite by ID.
        
        Args:
            user_id: ID of the user
            favorite_id: ID of the favorite
            
        Returns:
            Dictionary containing favorite information
            
        Raises:
            NotFoundError: If favorite not found
        """
        favorite = self.db.query(UserFavoriteSatellite).options(
            joinedload(UserFavoriteSatellite.satellite)
        ).filter(
            UserFavoriteSatellite.id == favorite_id,
            UserFavoriteSatellite.user_id == user_id
        ).first()
        
        if not favorite:
            raise NotFoundError(
                f"Favorite {favorite_id} not found for user {user_id}",
                resource_type="favorite",
                resource_id=str(favorite_id)
            )
        
        return {
            "id": favorite.id,
            "norad_id": favorite.norad_id,
            "name": favorite.satellite.name if favorite.satellite else f"Satellite {favorite.norad_id}",
            "category": favorite.satellite.category if favorite.satellite else "Unknown",
            "added_at": favorite.created_at
        }
    
    def is_satellite_favorite(self, user_id: int, norad_id: int) -> bool:
        """
        Check if a satellite is in user's favorites.
        
        Args:
            user_id: ID of the user
            norad_id: NORAD ID of the satellite
            
        Returns:
            True if satellite is in favorites, False otherwise
        """
        favorite = self.db.query(UserFavoriteSatellite).filter(
            UserFavoriteSatellite.user_id == user_id,
            UserFavoriteSatellite.norad_id == norad_id
        ).first()
        
        return favorite is not None
    
    def get_favorites_count(self, user_id: int) -> int:
        """
        Get the count of user's favorite satellites.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of favorite satellites
        """
        count = self.db.query(UserFavoriteSatellite).filter(
            UserFavoriteSatellite.user_id == user_id
        ).count()
        
        return count
    
    def get_favorite_norad_ids(self, user_id: int) -> List[int]:
        """
        Get list of NORAD IDs for user's favorite satellites.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of NORAD IDs
        """
        favorites = self.db.query(UserFavoriteSatellite.norad_id).filter(
            UserFavoriteSatellite.user_id == user_id
        ).all()
        
        return [favorite.norad_id for favorite in favorites]


# Dependency function for FastAPI
def get_favorite_service(db: Session = Depends(get_db)) -> FavoriteService:
    """Dependency function to get favorite service instance."""
    return FavoriteService(db)