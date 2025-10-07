"""
Database initialization script for the Satellite Tracker application.
"""

import logging
from sqlalchemy import text

from app.database import engine, init_db, check_db_connection
from app.redis_client import check_redis_connection

logger = logging.getLogger(__name__)


def create_database_if_not_exists():
    """
    Create the database if it doesn't exist.
    This is useful for initial setup.
    """
    try:
        # Try to connect to the database
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database already exists and is accessible")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def initialize_database():
    """
    Initialize the database with all required tables and indexes.
    """
    try:
        logger.info("Starting database initialization...")
        
        # Check database connection
        if not check_db_connection():
            raise Exception("Cannot connect to database")
        
        # Check Redis connection
        if not check_redis_connection():
            logger.warning("Redis connection failed - caching will not work")
        
        # Create all tables
        init_db()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    try:
        logger.warning("Resetting database - all data will be lost!")
        
        # Import all models to ensure they are registered
        from app.models import user, satellite, location, favorite, cache
        
        # Drop all tables
        from app.database import Base
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        logger.info("All tables recreated")
        
        logger.info("Database reset completed successfully")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Initialize database
    initialize_database()