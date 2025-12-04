"""
Configuration settings for the LiveKit Voice Agent.

Loads environment variables for:
- LiveKit server connection
- AI services (Deepgram, Google, AWS)
- Database connection
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required environment variables:
        - DEEPGRAM_API_KEY: For speech-to-text transcription
        - GEMINI_API_KEY: For LLM-powered conversation
        - AWS_ACCESS_KEY_ID: For text-to-speech synthesis
        - AWS_SECRET_ACCESS_KEY: For AWS authentication
        - AWS_DEFAULT_REGION: AWS region for Polly service
        - LIVEKIT_API_KEY: For LiveKit server authentication
        - LIVEKIT_API_SECRET: For LiveKit server authentication
        - LIVEKIT_URL: LiveKit server URL
        - DATABASE_URL: PostgreSQL connection string
    """
    # LiveKit
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    
    # AI Services
    DEEPGRAM_API_KEY: str
    GEMINI_API_KEY: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/insurance_db"
    
    # Backend API URL (for HTTP calls if needed)
    BACKEND_API_URL: str = "http://app:8000"


# Initialize settings singleton
settings = Settings()
