"""
User favorite satellites model for managing user's favorite satellite list.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserFavoriteSatellite(Base):
    """User favorite satellites model for storing user's favorite satellites."""
    
    __tablename__ = "user_favorite_satellites"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    norad_id = Column(Integer, ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="favorite_satellites")
    satellite = relationship("Satellite", back_populates="favorite_satellites")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'norad_id', name='uq_user_favorite_satellite'),
        Index('idx_user_favorites_user_id', 'user_id'),
        Index('idx_user_favorites_norad_id', 'norad_id'),
        Index('idx_user_favorites_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UserFavoriteSatellite(id={self.id}, user_id={self.user_id}, norad_id={self.norad_id})>"
    
    def to_dict(self):
        """Convert favorite satellite instance to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'norad_id': self.norad_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'satellite': self.satellite.to_dict() if self.satellite else None
        }
    
    def to_dict_with_position(self, position_data=None):
        """
        Convert favorite satellite instance to dictionary with position data.
        
        Args:
            position_data: Optional position data dictionary
            
        Returns:
            Dictionary with favorite satellite and position information
        """
        result = self.to_dict()
        if position_data:
            result['current_position'] = position_data
        return result