"""
Application configuration settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Insurance Voice Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/insurance_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # JWT / Auth
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # LiveKit
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_URL: str = "ws://livekit:7880"
    LIVEKIT_WEBHOOK_SECRET: Optional[str] = None
    
    # Twilio SIP
    TWILIO_SIP_DOMAIN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_SIP_USERNAME: str = ""
    TWILIO_SIP_PASSWORD: str = ""
    
    # AI Services
    DEEPGRAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    
    # CORS
    CORS_ORIGINS: str = "*"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
