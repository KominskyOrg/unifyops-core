from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings that can be configured via environment variables
    """
    # API settings
    API_TITLE: str = "UnifyOps Backend API"
    API_DESCRIPTION: str = "API for the UnifyOps platform"
    API_VERSION: str = "0.1.0"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    
    # Environment settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    
    # CORS settings
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # Database settings (if added later)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # Security settings
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings object
settings = Settings()

def get_settings() -> Settings:
    """
    Return the settings object for dependency injection
    """
    return settings 