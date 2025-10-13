"""
Favorites API endpoints for managing user's favorite satellites.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.schemas.favorite import (
    FavoriteCreate,
    FavoriteResponse,
    FavoritesListResponse,
    FavoriteBatchCreate,
    FavoriteBatchResponse,
    FavoriteDeleteResponse,
    FavoritesWithPositionsRequest
)
from app.services.favorite_service import FavoriteService, get_favorite_service
from app.utils.dependencies import get_db, get_current_user
from app.utils.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError,
    ExternalAPIError
)
from app.models.user import User

router = APIRouter(prefix="/users", tags=["favorites"])


@router.get(
    "/favorites",
    response_model=FavoritesListResponse,
    summary="Get user's favorite satellites",
    description="Retrieve all favorite satellites for the current user with optional position data."
)
async def get_user_favorites(
    include_positions: bool = Query(True, description="Include current position data for satellites"),
    use_cache: bool = Query(True, description="Use cached position data when available"),
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Get all favorite satellites for the current user.
    
    - **include_positions**: Whether to include current position data (requires user location)
    - **use_cache**: Whether to use cached position data for better performance
    
    Returns a list of favorite satellites with their details and optional position data.
    """
    try:
        favorites = await favorite_service.get_user_favorites(
            user_id=current_user.id,
            include_positions=include_positions,
            use_cache=use_cache
        )
        
        return FavoritesListResponse(
            favorites=favorites,
            total=len(favorites)
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve favorites"
        )


@router.post(
    "/favorites",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add satellite to favorites",
    description="Add a satellite to the user's favorites list by NORAD ID."
)
async def add_favorite_satellite(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Add a satellite to the user's favorites list.
    
    - **norad_id**: NORAD catalog number of the satellite (1-999999)
    
    The satellite information will be automatically retrieved and cached.
    """
    try:
        favorite = await favorite_service.add_favorite(
            user_id=current_user.id,
            norad_id=favorite_data.norad_id
        )
        
        return FavoriteResponse(**favorite)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ExternalAPIError as e:
        # Still create the favorite even if we can't get satellite details
        try:
            favorite = await favorite_service.add_favorite(
                user_id=current_user.id,
                norad_id=favorite_data.norad_id
            )
            return FavoriteResponse(**favorite)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to add satellite to favorites: {e.message}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add satellite to favorites"
        )


@router.post(
    "/favorites/batch",
    response_model=FavoriteBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add multiple satellites to favorites",
    description="Add multiple satellites to the user's favorites list in a single operation."
)
async def add_multiple_favorites(
    batch_data: FavoriteBatchCreate,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Add multiple satellites to the user's favorites list.
    
    - **norad_ids**: List of NORAD catalog numbers (1-50 satellites, 1-999999 each)
    
    Returns information about successfully added satellites and any that were skipped.
    """
    try:
        result = await favorite_service.add_multiple_favorites(
            user_id=current_user.id,
            norad_ids=batch_data.norad_ids
        )
        
        return FavoriteBatchResponse(**result)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add satellites to favorites"
        )


@router.delete(
    "/favorites/{favorite_id}",
    response_model=FavoriteDeleteResponse,
    summary="Remove satellite from favorites",
    description="Remove a satellite from the user's favorites list by favorite ID."
)
async def remove_favorite_satellite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Remove a satellite from the user's favorites list.
    
    - **favorite_id**: ID of the favorite entry to remove
    
    Returns confirmation of the removal.
    """
    try:
        result = favorite_service.remove_favorite(
            user_id=current_user.id,
            favorite_id=favorite_id
        )
        
        return FavoriteDeleteResponse(**result)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove satellite from favorites"
        )


@router.delete(
    "/favorites/satellite/{norad_id}",
    response_model=FavoriteDeleteResponse,
    summary="Remove satellite from favorites by NORAD ID",
    description="Remove a satellite from the user's favorites list by NORAD ID."
)
async def remove_favorite_by_norad_id(
    norad_id: int,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Remove a satellite from the user's favorites list by NORAD ID.
    
    - **norad_id**: NORAD catalog number of the satellite to remove
    
    Returns confirmation of the removal.
    """
    try:
        result = favorite_service.remove_favorite_by_norad_id(
            user_id=current_user.id,
            norad_id=norad_id
        )
        
        return FavoriteDeleteResponse(**result)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove satellite from favorites"
        )


@router.get(
    "/favorites/{favorite_id}",
    response_model=FavoriteResponse,
    summary="Get specific favorite satellite",
    description="Get details of a specific favorite satellite by favorite ID."
)
async def get_favorite_by_id(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Get details of a specific favorite satellite.
    
    - **favorite_id**: ID of the favorite entry
    
    Returns the favorite satellite information.
    """
    try:
        favorite = favorite_service.get_favorite_by_id(
            user_id=current_user.id,
            favorite_id=favorite_id
        )
        
        return FavoriteResponse(**favorite)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve favorite"
        )


@router.get(
    "/favorites/check/{norad_id}",
    summary="Check if satellite is in favorites",
    description="Check if a specific satellite is in the user's favorites list."
)
async def check_satellite_favorite(
    norad_id: int,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Check if a satellite is in the user's favorites list.
    
    - **norad_id**: NORAD catalog number of the satellite
    
    Returns whether the satellite is favorited and the favorite ID if it exists.
    """
    try:
        is_favorite = favorite_service.is_satellite_favorite(
            user_id=current_user.id,
            norad_id=norad_id
        )
        
        result = {
            "norad_id": norad_id,
            "is_favorite": is_favorite
        }
        
        if is_favorite:
            # Get the favorite details
            favorites = await favorite_service.get_user_favorites(
                user_id=current_user.id,
                include_positions=False
            )
            for fav in favorites:
                if fav["norad_id"] == norad_id:
                    result["favorite_id"] = fav["id"]
                    break
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check favorite status"
        )


@router.get(
    "/favorites/count",
    summary="Get favorites count",
    description="Get the total number of favorite satellites for the user."
)
async def get_favorites_count(
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Get the total number of favorite satellites for the user.
    
    Returns the count of satellites in the user's favorites list.
    """
    try:
        count = favorite_service.get_favorites_count(user_id=current_user.id)
        
        return {
            "user_id": current_user.id,
            "favorites_count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get favorites count"
        )


@router.get(
    "/favorites/norad-ids",
    response_model=List[int],
    summary="Get favorite NORAD IDs",
    description="Get a list of NORAD IDs for all favorite satellites."
)
async def get_favorite_norad_ids(
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    Get a list of NORAD IDs for all favorite satellites.
    
    Returns a simple list of NORAD IDs for quick reference.
    """
    try:
        norad_ids = favorite_service.get_favorite_norad_ids(user_id=current_user.id)
        return norad_ids
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get favorite NORAD IDs"
        )