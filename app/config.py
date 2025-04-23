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
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "unifyops-core")
    VERSION: str = os.getenv("VERSION", "0.1.0")

    # Logging settings
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    TASK_LOG_DIR: str = os.getenv("TASK_LOG_DIR", "logs/background_tasks")
    LOG_MAX_SIZE_MB: int = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    TERRAFORM_LOG_LEVEL: str = os.getenv("TERRAFORM_LOG_LEVEL", "info")
    LOG_STYLE: str = os.getenv("LOG_STYLE", "auto")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    # CORS settings
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5175")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS: str = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
    CORS_ALLOW_HEADERS: str = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization")

    # Database settings (if added later)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Security settings
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Terraform settings
    TERRAFORM_DIR: str = os.getenv("TERRAFORM_DIR", "tf")
    TERRAFORM_LOG_LEVEL: str = os.getenv("TERRAFORM_LOG_LEVEL", "info")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",")]

    @property
    def CORS_METHODS(self) -> List[str]:
        return [method.strip() for method in self.CORS_ALLOW_METHODS.split(",")]

    @property
    def CORS_HEADERS(self) -> List[str]:
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",")]

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
