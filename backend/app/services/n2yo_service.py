"""
N2YO API client service for satellite data retrieval.
Handles API communication, rate limiting, and error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import httpx
from fastapi import HTTPException

from app.config import settings
from app.utils.exceptions import ExternalAPIError, RateLimitExceededError, ConfigurationError

logger = logging.getLogger(__name__)


# Use custom exceptions from utils.exceptions


class N2YOService:
    """Service for interacting with the N2YO API."""
    
    def __init__(self):
        self.base_url = settings.n2yo_base_url
        self.api_key = settings.n2yo_api_key
        self.client = None
        self._rate_limit_reset = None
        self._requests_remaining = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _check_api_key(self) -> None:
        """Check if API key is configured."""
        if not self.api_key:
            raise ConfigurationError("N2YO API key not configured", config_key="n2yo_api_key")
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the N2YO API with error handling and rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            ExternalAPIError: For API-related errors
            RateLimitExceededError: When rate limit is exceeded
        """
        self._check_api_key()
        
        if not self.client:
            raise ExternalAPIError("HTTP client not initialized. Use async context manager.", api_name="N2YO")
        
        # Add API key to parameters
        params["apiKey"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.info(f"Making N2YO API request to {endpoint} with params: {params}")
            
            response = await self.client.get(url, params=params)
            
            # Update rate limit info from headers
            self._update_rate_limit_info(response.headers)
            
            # Handle rate limiting
            if response.status_code == 429:
                reset_time = self._rate_limit_reset or datetime.utcnow() + timedelta(hours=1)
                raise RateLimitExceededError(
                    f"Rate limit exceeded. Resets at {reset_time}",
                    reset_time=reset_time.isoformat()
                )
            
            # Handle other HTTP errors
            if response.status_code != 200:
                error_msg = f"N2YO API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ExternalAPIError(error_msg, api_name="N2YO", status_code=response.status_code)
            
            data = response.json()
            
            # Check for API-specific errors
            if "error" in data:
                error_msg = f"N2YO API returned error: {data['error']}"
                logger.error(error_msg)
                raise ExternalAPIError(error_msg, api_name="N2YO")
            
            logger.info(f"N2YO API request successful. Requests remaining: {self._requests_remaining}")
            return data
            
        except httpx.TimeoutException:
            error_msg = "N2YO API request timed out"
            logger.error(error_msg)
            raise ExternalAPIError(error_msg, api_name="N2YO")
        except httpx.RequestError as e:
            error_msg = f"N2YO API request failed: {str(e)}"
            logger.error(error_msg)
            raise ExternalAPIError(error_msg, api_name="N2YO")
    
    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers."""
        try:
            if "X-RateLimit-Remaining" in headers:
                self._requests_remaining = int(headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in headers:
                reset_timestamp = int(headers["X-RateLimit-Reset"])
                self._rate_limit_reset = datetime.utcfromtimestamp(reset_timestamp)
        except (ValueError, KeyError):
            # Headers might not be present or in expected format
            pass
    
    async def search_satellites(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for satellites by name.
        
        Note: N2YO API doesn't have a direct search endpoint, so this is a placeholder
        that returns an empty list. In a real implementation, you would need to:
        1. Maintain a local database of satellite names and NORAD IDs
        2. Use a different API that supports search
        3. Or implement a workaround using known satellite lists
        
        Args:
            query: Search query (satellite name)
            category: Optional category filter
            
        Returns:
            List of satellite information dictionaries
        """
        try:
            # For now, return empty list since N2YO doesn't support direct search
            # In a real implementation, you would search a local database or use
            # a different approach
            logger.warning(f"N2YO API doesn't support direct search. Query: {query}")
            return []
            
        except Exception as e:
            logger.error(f"Error searching satellites: {str(e)}")
            raise ExternalAPIError(f"Failed to search satellites: {str(e)}", api_name="N2YO")
    
    async def get_satellite_info(self, norad_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific satellite.
        
        Args:
            norad_id: NORAD ID of the satellite
            
        Returns:
            Satellite information dictionary
        """
        try:
            # Get basic satellite info using TLE endpoint
            data = await self._make_request(f"satellite/tle/{norad_id}", {})
            
            
            if "tle" in data:
                tle_data = data["tle"]
                
                # Check if we have satellite name in the response
                sat_name = data.get("info", {}).get("satname") if isinstance(data.get("info"), dict) else None
                
                if not sat_name:
                    # TLE data might be a string or dict, handle both cases
                    if isinstance(tle_data, str):
                        # Parse satellite name from TLE string if possible
                        lines = tle_data.strip().split('\n')
                        # TLE format: line 0 is satellite name, line 1 and 2 are orbital elements
                        if len(lines) >= 3:
                            sat_name = lines[0].strip()
                        else:
                            sat_name = f"Satellite {norad_id}"
                    else:
                        sat_name = tle_data.get("satname", f"Satellite {norad_id}")
                
                satellite_info = {
                    "norad_id": norad_id,
                    "name": sat_name,
                    "launch_date": None,  # Not available in TLE data
                    "country": None,      # Not available in TLE data
                    "category": None      # Not available in TLE data
                }
                
                logger.info(f"Retrieved satellite info for NORAD ID: {norad_id}")
                return satellite_info
            else:
                raise ExternalAPIError(f"No data found for satellite {norad_id}", api_name="N2YO")
                
        except Exception as e:
            logger.error(f"Error getting satellite info for {norad_id}: {str(e)}")
            raise ExternalAPIError(f"Failed to get satellite info: {str(e)}", api_name="N2YO")
    
    async def get_satellite_position(self, norad_id: int, latitude: float, longitude: float, altitude: float = 0) -> Dict[str, Any]:
        """
        Get current position of a satellite.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            
        Returns:
            Satellite position data
        """
        try:
            params = {
                "id": norad_id,
                "lat": latitude,
                "lng": longitude,
                "alt": altitude / 1000,  # Convert to kilometers
                "seconds": 1  # Get current position
            }
            
            data = await self._make_request(f"satellite/positions/{norad_id}/{latitude}/{longitude}/{altitude/1000}/1", params)
            
            if "positions" in data and len(data["positions"]) > 0:
                pos = data["positions"][0]
                
                position_data = {
                    "latitude": Decimal(str(pos.get("satlatitude", 0))),
                    "longitude": Decimal(str(pos.get("satlongitude", 0))),
                    "altitude": Decimal(str(pos.get("sataltitude", 0))),
                    "velocity": Decimal(str(pos.get("velocity", 0))),
                    "timestamp": datetime.utcfromtimestamp(pos.get("timestamp", 0))
                }
                
                logger.info(f"Retrieved position for satellite {norad_id}")
                return position_data
            else:
                raise ExternalAPIError(f"No position data found for satellite {norad_id}", api_name="N2YO")
                
        except Exception as e:
            logger.error(f"Error getting satellite position for {norad_id}: {str(e)}")
            raise ExternalAPIError(f"Failed to get satellite position: {str(e)}", api_name="N2YO")
    
    async def get_satellite_passes(self, norad_id: int, latitude: float, longitude: float, altitude: float = 0, days: int = 10) -> List[Dict[str, Any]]:
        """
        Get upcoming passes of a satellite over a location.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            altitude: Observer altitude in meters
            days: Number of days to predict (max 10)
            
        Returns:
            List of pass prediction dictionaries
        """
        try:
            # Ensure days is within API limits
            days = min(max(days, 1), 10)
            
            params = {
                "id": norad_id,
                "lat": latitude,
                "lng": longitude,
                "alt": altitude / 1000,  # Convert to kilometers
                "days": days,
                "min_elevation": 0  # Include all passes
            }
            
            data = await self._make_request(f"satellite/visualpasses/{norad_id}/{latitude}/{longitude}/{altitude/1000}/{days}/0", params)
            
            passes = []
            if "passes" in data:
                for pass_data in data["passes"]:
                    pass_info = {
                        "start_time": datetime.utcfromtimestamp(pass_data.get("startUTC", 0)),
                        "end_time": datetime.utcfromtimestamp(pass_data.get("endUTC", 0)),
                        "duration": pass_data.get("duration", 0),
                        "max_elevation": Decimal(str(pass_data.get("maxEl", 0))),
                        "start_azimuth": Decimal(str(pass_data.get("startAz", 0))),
                        "end_azimuth": Decimal(str(pass_data.get("endAz", 0))),
                        "magnitude": Decimal(str(pass_data.get("mag", 0))) if pass_data.get("mag") is not None else None,
                        "visibility": "visible" if pass_data.get("maxEl", 0) > 0 else "not_visible"
                    }
                    passes.append(pass_info)
            
            logger.info(f"Retrieved {len(passes)} passes for satellite {norad_id}")
            return passes
            
        except Exception as e:
            logger.error(f"Error getting satellite passes for {norad_id}: {str(e)}")
            raise ExternalAPIError(f"Failed to get satellite passes: {str(e)}", api_name="N2YO")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        return {
            "requests_remaining": self._requests_remaining,
            "reset_time": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None
        }


# Singleton instance for dependency injection
n2yo_service = N2YOService()


async def get_n2yo_service() -> N2YOService:
    """Dependency function to get N2YO service instance."""
    return n2yo_service