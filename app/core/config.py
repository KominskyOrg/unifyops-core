from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv
from pydantic import field_validator

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

    # Logging settings
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    TASK_LOG_DIR: str = os.getenv("TASK_LOG_DIR", "logs/background_tasks")
    LOG_MAX_SIZE_MB: int = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    TERRAFORM_LOG_LEVEL: str = os.getenv("TERRAFORM_LOG_LEVEL", "info")

    # CORS settings
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8000"

    # Database settings (if added later)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Security settings
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Terraform settings
    TERRAFORM_DIR: str = os.getenv("TERRAFORM_DIR", "tf")
    TERRAFORM_LOG_LEVEL: str = os.getenv("TERRAFORM_LOG_LEVEL", "info")

    @field_validator("CORS_ORIGINS_STR", mode="before")
    def assemble_cors_origins(cls, v: Optional[str]) -> str:
        return os.getenv("CORS_ORIGINS", v)

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",")]

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
