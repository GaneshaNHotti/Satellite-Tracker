"""
User location model for storing user geographical coordinates.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, CheckConstraint, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.database import Base


class UserLocation(Base):
    """User location model for storing geographical coordinates."""
    
    __tablename__ = "user_locations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Geographical coordinates
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    
    # Optional address information
    address = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="locations")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude_range'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude_range'),
        Index('idx_user_locations_user_id', 'user_id'),
        Index('idx_user_locations_coords', 'latitude', 'longitude'),
        Index('idx_user_locations_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UserLocation(id={self.id}, user_id={self.user_id}, lat={self.latitude}, lon={self.longitude})>"
    
    def to_dict(self):
        """Convert location instance to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def validate_coordinates(cls, latitude: Decimal, longitude: Decimal) -> bool:
        """
        Validate that coordinates are within valid ranges.
        Returns True if valid, False otherwise.
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, TypeError):
            return False