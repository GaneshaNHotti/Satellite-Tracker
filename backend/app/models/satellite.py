"""
Satellite model for storing satellite information from N2YO API.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date

from app.database import Base


class Satellite(Base):
    """Satellite model for caching satellite information."""
    
    __tablename__ = "satellites"
    
    # Primary key (NORAD ID)
    norad_id = Column(Integer, primary_key=True, index=True)
    
    # Satellite information
    name = Column(String(255), nullable=False, index=True)
    launch_date = Column(Date, nullable=True)
    country = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    favorite_satellites = relationship("UserFavoriteSatellite", back_populates="satellite", cascade="all, delete-orphan")
    position_cache = relationship("SatellitePositionCache", back_populates="satellite", cascade="all, delete-orphan")
    passes_cache = relationship("SatellitePassCache", back_populates="satellite", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_satellites_name', 'name'),
        Index('idx_satellites_category', 'category'),
        Index('idx_satellites_country', 'country'),
        Index('idx_satellites_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Satellite(norad_id={self.norad_id}, name='{self.name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert satellite instance to dictionary."""
        return {
            'norad_id': self.norad_id,
            'name': self.name,
            'launch_date': self.launch_date.isoformat() if self.launch_date else None,
            'country': self.country,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_n2yo_data(cls, data: dict):
        """
        Create Satellite instance from N2YO API data.
        
        Args:
            data: Dictionary containing satellite data from N2YO API
            
        Returns:
            Satellite instance
        """
        launch_date = None
        if data.get('launchDate'):
            try:
                launch_date = datetime.strptime(data['launchDate'], '%Y-%m-%d').date()
            except ValueError:
                pass  # Keep as None if date parsing fails
        
        return cls(
            norad_id=data.get('noradID'),
            name=data.get('satname', '').strip(),
            launch_date=launch_date,
            country=data.get('country', '').strip() or None,
            category=data.get('category', '').strip() or None
        )