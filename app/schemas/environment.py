from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.models.environment import EnvironmentStatus


class EnvironmentBase(BaseModel):
    """Base model for environment operations"""

    name: str = Field(..., description="Name of the environment")
    module_path: str = Field(
        ..., description="Path to the Terraform module relative to the tf directory"
    )
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Variables to pass to the Terraform module"
    )


class EnvironmentCreate(EnvironmentBase):
    """Model for creating a new environment"""

    auto_apply: bool = Field(True, description="Whether to automatically apply the Terraform plan after creation")


class EnvironmentResponse(EnvironmentBase):
    """Response model for environment operations"""

    id: str = Field(..., description="Unique identifier for the environment")
    status: str = Field(..., description="Current status of the environment")
    created_at: datetime = Field(..., description="Timestamp when the environment was created")
    updated_at: datetime = Field(..., description="Timestamp when the environment was last updated")
    error_message: Optional[str] = Field(
        None, description="Error message if the environment provisioning failed"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "12345678-1234-5678-1234-567812345678",
                "name": "dev-environment",
                "module_path": "aws/vpc",
                "status": "provisioning",
                "variables": {
                    "region": "us-west-2",
                    "vpc_cidr": "10.0.0.0/16",
                    "environment": "dev",
                },
                "created_at": "2023-05-18T14:30:00Z",
                "updated_at": "2023-05-18T14:30:00Z",
                "error_message": None,
            }
        }


class EnvironmentListResponse(BaseModel):
    """Response model for listing environments"""

    environments: List[EnvironmentResponse] = Field(..., description="List of environments")
    count: int = Field(..., description="Total number of environments")

    class Config:
        schema_extra = {
            "example": {
                "environments": [
                    {
                        "id": "12345678-1234-5678-1234-567812345678",
                        "name": "dev-environment",
                        "module_path": "aws/vpc",
                        "status": "provisioned",
                        "variables": {
                            "region": "us-west-2",
                            "vpc_cidr": "10.0.0.0/16",
                            "environment": "dev",
                        },
                        "created_at": "2023-05-18T14:30:00Z",
                        "updated_at": "2023-05-18T14:35:00Z",
                        "error_message": None,
                    }
                ],
                "count": 1,
            }
        }


class EnvironmentStatusResponse(BaseModel):
    """Response model for environment status information"""
    id: str = Field(..., description="Unique identifier for the environment")
    name: str = Field(..., description="Name of the environment")
    status: str = Field(..., description="Current status of the environment")
    
    # Execution IDs
    init_execution_id: Optional[str] = Field(None, description="ID of the most recent init execution")
    plan_execution_id: Optional[str] = Field(None, description="ID of the most recent plan execution")
    apply_execution_id: Optional[str] = Field(None, description="ID of the most recent apply execution")
    
    # Timestamps
    created_at: datetime = Field(..., description="Timestamp when the environment was created")
    updated_at: datetime = Field(..., description="Timestamp when the environment was last updated")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if the environment provisioning failed")
    
    # Resources
    resource_count: Optional[int] = Field(None, description="Number of resources managed by this environment")
    state_file: Optional[str] = Field(None, description="Path to the Terraform state file")
    
    # Outputs if available
    outputs: Optional[Dict[str, Any]] = Field(None, description="Terraform outputs if available")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "12345678-1234-5678-1234-567812345678",
                "name": "dev-environment",
                "status": "provisioned",
                "init_execution_id": "init-a1b2c3d4e5",
                "plan_execution_id": "plan-b2c3d4e5f6",
                "apply_execution_id": "apply-c3d4e5f6g7",
                "created_at": "2023-05-18T14:30:00Z",
                "updated_at": "2023-05-18T14:45:00Z",
                "error_message": None,
                "resource_count": 12,
                "state_file": "terraform.12345678-1234-5678-1234-567812345678.tfstate",
                "outputs": {
                    "vpc_id": "vpc-0123456789abcdef0",
                    "subnet_ids": ["subnet-abc123", "subnet-def456"]
                }
            }
        }
