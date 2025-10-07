import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database settings
    database_url: str = os.getenv("DATABASE_URL")
    
    # Redis settings
    redis_url: str = os.getenv("REDIS_URL")
    
    # JWT settings
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 90  # 90 minutes
    
    # N2YO API settings
    n2yo_api_key: str = os.getenv("N2YO_API_KEY")
    n2yo_base_url: str = "https://api.n2yo.com/rest/v1"
    
    # Cache settings
    satellite_position_cache_ttl: int = 300  # 5 minutes
    satellite_passes_cache_ttl: int = 86400  # 24 hours
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    
    class Config:
        env_file = ".env"

settings = Settings()