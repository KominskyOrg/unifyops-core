from fastapi import Depends
from typing import Optional
import os

from app.core.environment import EnvironmentService
from app.core.terraform import TerraformService
from app.config import Settings

# Create services
terraform_service = TerraformService(Settings.TERRAFORM_DIR)
environment_service = EnvironmentService(terraform_service)

# Service dependencies
def get_terraform_service() -> TerraformService:
    """
    Dependency for TerraformService
    """
    return terraform_service


def get_environment_service() -> EnvironmentService:
    """
    Dependency for EnvironmentService
    """
    return environment_service 