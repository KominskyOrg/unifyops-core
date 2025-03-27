from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response model for API errors"""

    detail: str = Field(..., description="Error message describing the issue")

    class Config:
        schema_extra = {"example": {"detail": "Module not found: aws/unknown_module"}}


class TerraformModule(BaseModel):
    """Model for Terraform module information"""

    name: str = Field(..., description="Name of the Terraform module")
    path: str = Field(..., description="Path to the module relative to the tf directory")
    description: str = Field(..., description="Description of the module functionality")

    class Config:
        schema_extra = {
            "example": {
                "name": "aws_s3_bucket",
                "path": "aws/s3_bucket",
                "description": "Creates an AWS S3 bucket with standard configuration",
            }
        }


# Base request models
class TerraformRequest(BaseModel):
    """Base model for Terraform operation requests"""

    module_path: str = Field(
        ..., description="Path to the Terraform module relative to the tf directory"
    )
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Variables to pass to the Terraform module"
    )


class TerraformInitRequest(TerraformRequest):
    """Model for Terraform init requests"""

    backend_config: Optional[Dict[str, str]] = Field(
        None, description="Backend configuration for Terraform state"
    )
    force_module_download: bool = Field(False, description="Force downloading modules from source")

    class Config:
        schema_extra = {
            "example": {
                "module_path": "aws/s3_bucket",
                "backend_config": {
                    "bucket": "terraform-state-bucket",
                    "key": "s3-module/terraform.tfstate",
                    "region": "us-west-2",
                },
                "force_module_download": False,
            }
        }


class TerraformPlanRequest(TerraformRequest):
    """Model for Terraform plan requests"""

    class Config:
        schema_extra = {
            "example": {
                "module_path": "aws/s3_bucket",
                "variables": {
                    "bucket_name": "my-application-bucket",
                    "region": "us-west-2",
                    "tags": {"Environment": "Production", "Project": "DataLake"},
                },
            }
        }


class TerraformApplyRequest(TerraformRequest):
    """Model for Terraform apply requests"""

    auto_approve: bool = Field(
        False, description="Whether to auto-approve the apply without confirmation"
    )
    plan_id: Optional[str] = Field(None, description="ID of a previously created plan to apply")

    class Config:
        schema_extra = {
            "example": {
                "module_path": "aws/s3_bucket",
                "variables": {
                    "bucket_name": "my-application-bucket",
                    "region": "us-west-2",
                    "tags": {"Environment": "Production", "Project": "DataLake"},
                },
                "auto_approve": True,
                "plan_id": "plan-1234567890",
            }
        }


class TerraformDestroyRequest(TerraformRequest):
    """Model for Terraform destroy requests"""

    auto_approve: bool = Field(
        False, description="Whether to auto-approve the destroy without confirmation"
    )

    class Config:
        schema_extra = {
            "example": {
                "module_path": "aws/s3_bucket",
                "variables": {"bucket_name": "my-application-bucket", "region": "us-west-2"},
                "auto_approve": True,
            }
        }


# Base response models
class TerraformBaseResponse(BaseModel):
    """Base model for all Terraform operation responses"""

    operation: str = Field(..., description="The Terraform operation that was performed")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(
        ..., description="A human-readable message describing the result of the operation"
    )
    execution_id: str = Field(..., description="A unique ID for the execution")
    duration_ms: float = Field(..., description="Duration of the operation in milliseconds")


class TerraformInitResponse(TerraformBaseResponse):
    """Response model for Terraform init operation"""

    class Config:
        schema_extra = {
            "example": {
                "operation": "INIT",
                "success": True,
                "message": "Terraform module initialized successfully",
                "execution_id": "init-a1b2c3d4",
                "duration_ms": 1234.56,
            }
        }


class TerraformPlanResponse(TerraformBaseResponse):
    """Response model for Terraform plan operation"""

    plan_id: str = Field(..., description="ID of the created plan")

    class Config:
        schema_extra = {
            "example": {
                "operation": "PLAN",
                "success": True,
                "message": "Terraform plan created successfully",
                "execution_id": "plan-b2c3d4e5",
                "duration_ms": 2345.67,
                "plan_id": "plan-1234567890",
            }
        }


class TerraformApplyResponse(TerraformBaseResponse):
    """Response model for Terraform apply operation"""

    outputs: Dict[str, Any] = Field(..., description="Terraform outputs from the apply operation")

    class Config:
        schema_extra = {
            "example": {
                "operation": "APPLY",
                "success": True,
                "message": "Terraform apply completed successfully",
                "execution_id": "apply-c3d4e5f6",
                "duration_ms": 3456.78,
                "outputs": {
                    "bucket_name": "my-application-bucket",
                    "bucket_arn": "arn:aws:s3:::my-application-bucket",
                    "bucket_region": "us-west-2",
                },
            }
        }


class TerraformDestroyResponse(TerraformBaseResponse):
    """Response model for Terraform destroy operation"""

    class Config:
        schema_extra = {
            "example": {
                "operation": "DESTROY",
                "success": True,
                "message": "Terraform destroy completed successfully",
                "execution_id": "destroy-d4e5f6g7",
                "duration_ms": 2567.89,
            }
        }


class ModulesResponse(BaseModel):
    """Response model for listing Terraform modules"""

    modules: List[TerraformModule] = Field(..., description="List of available Terraform modules")
    count: int = Field(..., description="Total number of modules")

    class Config:
        schema_extra = {
            "example": {
                "modules": [
                    {
                        "name": "aws_s3_bucket",
                        "path": "aws/s3_bucket",
                        "description": "Creates an AWS S3 bucket with standard configuration",
                    },
                    {
                        "name": "aws_lambda",
                        "path": "aws/lambda",
                        "description": "Deploys an AWS Lambda function with IAM role",
                    },
                ],
                "count": 2,
            }
        }


class OutputsResponse(BaseModel):
    """Response model for Terraform outputs"""

    module: str = Field(..., description="Path to the Terraform module")
    outputs: Dict[str, Any] = Field(..., description="Map of output names to values")

    class Config:
        schema_extra = {
            "example": {
                "module": "aws/s3_bucket",
                "outputs": {
                    "bucket_arn": "arn:aws:s3:::my-application-bucket",
                    "bucket_domain_name": "my-application-bucket.s3.amazonaws.com",
                    "bucket_regional_domain_name": "my-application-bucket.s3.us-west-2.amazonaws.com",
                },
            }
        }
