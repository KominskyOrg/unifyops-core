from fastapi import Depends
import os

from app.core.environment import EnvironmentService
from app.core.resource import ResourceService
from app.core.terraform import TerraformService
from app.core.config import settings

# Base Terraform directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TF_DIR = os.path.join(BASE_DIR, "app/tf")


def get_terraform_service() -> TerraformService:
    """
    Dependency for TerraformService
    """
    return TerraformService(TF_DIR)


def get_environment_service(
    terraform_service: TerraformService = Depends(get_terraform_service),
) -> EnvironmentService:
    """
    Dependency for EnvironmentService
    """
    return EnvironmentService(terraform_service)


def get_resource_service(
    terraform_service: TerraformService = Depends(get_terraform_service),
) -> ResourceService:
    """
    Dependency for ResourceService
    """
    return ResourceService(terraform_service) 