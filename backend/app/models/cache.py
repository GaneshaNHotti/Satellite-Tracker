"""
Cache models for storing satellite positions and pass predictions.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.database import Base


class SatellitePositionCache(Base):
    """Cache model for storing satellite position data."""
    
    __tablename__ = "satellite_positions_cache"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to satellite
    norad_id = Column(Integer, ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Position data
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    altitude = Column(DECIMAL(10, 2), nullable=False)  # in kilometers
    velocity = Column(DECIMAL(10, 2), nullable=False)  # in km/s
    
    # Timestamp of the position data
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Cache metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    satellite = relationship("Satellite", back_populates="position_cache")
    
    # Indexes
    __table_args__ = (
        Index('idx_positions_cache_norad_timestamp', 'norad_id', 'timestamp', postgresql_using='btree'),
        Index('idx_positions_cache_timestamp', 'timestamp'),
        Index('idx_positions_cache_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SatellitePositionCache(id={self.id}, norad_id={self.norad_id}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """Convert position cache instance to dictionary."""
        return {
            'id': self.id,
            'norad_id': self.norad_id,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'altitude': float(self.altitude) if self.altitude else None,
            'velocity': float(self.velocity) if self.velocity else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_n2yo_data(cls, norad_id: int, data: dict):
        """
        Create SatellitePositionCache instance from N2YO API position data.
        
        Args:
            norad_id: NORAD ID of the satellite
            data: Dictionary containing position data from N2YO API
            
        Returns:
            SatellitePositionCache instance
        """
        # Parse timestamp from N2YO format
        timestamp = datetime.utcnow()  # Default to current time
        if data.get('timestamp'):
            try:
                timestamp = datetime.fromtimestamp(data['timestamp'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            norad_id=norad_id,
            latitude=data.get('satlatitude', 0),
            longitude=data.get('satlongitude', 0),
            altitude=data.get('sataltitude', 0),
            velocity=data.get('satvelocity', 0),
            timestamp=timestamp
        )
    
    def is_expired(self, ttl_minutes: int = 5) -> bool:
        """
        Check if the cached position data is expired.
        
        Args:
            ttl_minutes: Time to live in minutes (default: 5)
            
        Returns:
            True if expired, False otherwise
        """
        if not self.created_at:
            return True
        
        expiry_time = self.created_at + timedelta(minutes=ttl_minutes)
        return datetime.utcnow() > expiry_time


class SatellitePassCache(Base):
    """Cache model for storing satellite pass prediction data."""
    
    __tablename__ = "satellite_passes_cache"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to satellite
    norad_id = Column(Integer, ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Location for which the pass was calculated
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    
    # Pass timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    # Pass characteristics
    max_elevation = Column(DECIMAL(5, 2), nullable=False)  # in degrees
    start_azimuth = Column(DECIMAL(5, 2), nullable=True)   # in degrees
    end_azimuth = Column(DECIMAL(5, 2), nullable=True)     # in degrees
    magnitude = Column(DECIMAL(4, 2), nullable=True)       # brightness magnitude
    
    # Cache metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    satellite = relationship("Satellite", back_populates="passes_cache")
    
    # Indexes
    __table_args__ = (
        Index('idx_passes_cache_location_time', 'latitude', 'longitude', 'start_time'),
        Index('idx_passes_cache_norad_time', 'norad_id', 'start_time'),
        Index('idx_passes_cache_expires', 'expires_at'),
        Index('idx_passes_cache_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SatellitePassCache(id={self.id}, norad_id={self.norad_id}, start_time={self.start_time})>"
    
    def to_dict(self):
        """Convert pass cache instance to dictionary."""
        duration = None
        if self.start_time and self.end_time:
            duration = int((self.end_time - self.start_time).total_seconds())
        
        return {
            'id': self.id,
            'norad_id': self.norad_id,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': duration,
            'max_elevation': float(self.max_elevation) if self.max_elevation else None,
            'start_azimuth': float(self.start_azimuth) if self.start_azimuth else None,
            'end_azimuth': float(self.end_azimuth) if self.end_azimuth else None,
            'magnitude': float(self.magnitude) if self.magnitude else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_n2yo_data(cls, norad_id: int, latitude: float, longitude: float, data: dict, ttl_hours: int = 24):
        """
        Create SatellitePassCache instance from N2YO API pass data.
        
        Args:
            norad_id: NORAD ID of the satellite
            latitude: Observer latitude
            longitude: Observer longitude
            data: Dictionary containing pass data from N2YO API
            ttl_hours: Time to live in hours (default: 24)
            
        Returns:
            SatellitePassCache instance
        """
        # Parse timestamps from N2YO format
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        if data.get('startUTC'):
            try:
                start_time = datetime.fromtimestamp(data['startUTC'])
            except (ValueError, TypeError):
                pass
        
        if data.get('endUTC'):
            try:
                end_time = datetime.fromtimestamp(data['endUTC'])
            except (ValueError, TypeError):
                pass
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        return cls(
            norad_id=norad_id,
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
            max_elevation=data.get('maxElevation', 0),
            start_azimuth=data.get('startAz'),
            end_azimuth=data.get('endAz'),
            magnitude=data.get('mag'),
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """
        Check if the cached pass data is expired.
        
        Returns:
            True if expired, False otherwise
        """
        if not self.expires_at:
            return True
        
        return datetime.utcnow() > self.expires_at
    
    def get_visibility(self) -> str:
        """
        Determine visibility status based on magnitude and elevation.
        
        Returns:
            String indicating visibility: 'visible', 'dim', 'not_visible'
        """
        if self.max_elevation < 10:
            return 'not_visible'
        elif self.magnitude and self.magnitude > 4:
            return 'dim'
        else:
            return 'visible'