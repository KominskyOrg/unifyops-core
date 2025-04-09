from fastapi import Depends
from typing import Optional
import os

from app.core.environment import EnvironmentService
from app.core.terraform import TerraformService
from app.core.config import get_settings, Settings

# Base directory for Terraform operations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TF_DIR = os.path.join(BASE_DIR, "app/tf")

# Create services
terraform_service = TerraformService(TF_DIR)
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