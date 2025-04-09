from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime


class UUIDModelMixin:
    """Mixin to automatically convert UUID objects to strings for comparison."""
    
    def __eq__(self, other):
        if isinstance(other, (str, UUID)):
            for field_name, field_type in self.__annotations__.items():
                if field_type == UUID and hasattr(self, field_name):
                    uuid_field = getattr(self, field_name)
                    if uuid_field is not None and str(uuid_field) == str(other):
                        return True
        return super().__eq__(other)


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


# Base schemas 

class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    organization_id: UUID


class EnvironmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    organization_id: UUID
    team_id: Optional[UUID] = None
    variables: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class ResourceBase(BaseModel):
    name: str
    module_path: str
    resource_type: str
    provider: str
    variables: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    
    @validator('position_x', 'position_y')
    def validate_positions(cls, v):
        if v is not None and v < 0:
            raise ValueError("Position values cannot be negative")
        return v


class ConnectionBase(BaseModel):
    source_id: UUID
    target_id: UUID
    connection_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class CloudCredentialBase(BaseModel):
    name: str
    provider: str
    organization_id: UUID
    credentials: Dict[str, Any]
    is_default: bool = False


class ComplianceRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    provider: Optional[str] = None
    resource_type: Optional[str] = None
    rule_definition: Dict[str, Any]
    severity: str
    enabled: bool = True


class DeploymentBase(BaseModel):
    environment_id: UUID
    execution_id: str
    operation: str
    status: str
    initiated_by: str


# Create request schemas

class OrganizationCreate(OrganizationBase):
    pass


class TeamCreate(TeamBase):
    pass


class EnvironmentCreate(EnvironmentBase):
    created_by: str


class ResourceCreate(ResourceBase):
    environment_id: UUID


class ConnectionCreate(ConnectionBase):
    pass


class CloudCredentialCreate(CloudCredentialBase):
    pass


class ComplianceRuleCreate(ComplianceRuleBase):
    pass


class DeploymentCreate(BaseModel):
    environment_id: UUID
    operation: str
    initiated_by: str


# Update request schemas

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    organization_id: Optional[UUID] = None


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[UUID] = None
    variables: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    
    @validator('position_x', 'position_y')
    def validate_positions(cls, v):
        if v is not None and v < 0:
            raise ValueError("Position values cannot be negative")
        return v


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class CloudCredentialUpdate(BaseModel):
    name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class ComplianceRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_definition: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


# Response schemas

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TeamResponse(TeamBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ResourceResponse(ResourceBase):
    id: UUID
    environment_id: UUID
    state: str
    outputs: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConnectionResponse(ConnectionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DeploymentResponse(BaseModel):
    id: UUID
    environment_id: UUID
    execution_id: str
    operation: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    initiated_by: str
    output: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class EnvironmentResponse(EnvironmentBase):
    id: UUID
    status: str
    created_by: str
    terraform_dir: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_deployed_at: Optional[datetime] = None
    estimated_cost: Optional[float] = None
    resources: List[ResourceResponse] = []
    connections: List[ConnectionResponse] = []
    
    class Config:
        orm_mode = True


class EnvironmentDetailResponse(EnvironmentResponse):
    resources: List[ResourceResponse] = []
    deployments: List[DeploymentResponse] = []

    class Config:
        orm_mode = True


class CloudCredentialResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    organization_id: UUID
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ComplianceRuleResponse(ComplianceRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Special purpose schemas

class ResourcePositionUpdate(BaseModel):
    """Request to update a resource's position in the designer"""
    position_x: int
    position_y: int
    
    @validator('position_x', 'position_y')
    def validate_positions(cls, v):
        if v < 0:
            raise ValueError("Position values cannot be negative")
        return v


class EnvironmentDeployRequest(BaseModel):
    """Request to deploy an environment"""
    auto_approve: bool = False
    variables: Optional[Dict[str, Any]] = None


class EnvironmentResourcesRequest(BaseModel):
    """Request to add multiple resources to an environment at once"""
    resources: List[ResourceCreate]
    connections: Optional[List[ConnectionCreate]] = None


class DesignerStateRequest(BaseModel):
    """Request to save the complete designer state for an environment"""
    resources: List[ResourceCreate]
    connections: List[ConnectionCreate]


class DesignerStateResponse(BaseModel):
    """Complete designer state for an environment"""
    environment_id: UUID
    resources: List[ResourceResponse]
    connections: List[ConnectionResponse]

    class Config:
        orm_mode = True


class GenerateTerraformRequest(BaseModel):
    """Request to generate Terraform code for an environment"""
    environment_id: UUID
    pretty_print: bool = False


class DeployEnvironmentRequest(BaseModel):
    """Request to deploy an environment"""
    environment_id: UUID
    initiated_by: str = "system"


class ApplyModuleRequest(BaseModel):
    """Request to apply a specific module to an environment"""
    environment_id: UUID
    module_path: str
    variables: Optional[Dict[str, Any]] = None


class TemplateVariableResponse(BaseModel):
    """Response model for a template variable"""
    name: str
    type: str
    description: str
    default: Optional[Any] = None
    required: bool = False


class TemplateOutputResponse(BaseModel):
    """Response model for a template output"""
    name: str
    description: str
    value: str


class TemplateDetailsResponse(BaseModel):
    """Response model for template details"""
    name: str
    description: str
    provider: str
    variables: List[TemplateVariableResponse]
    outputs: List[TemplateOutputResponse]
    resource_types: List[str]


class CreateModuleFromTemplateRequest(BaseModel):
    """Request to create a module from a template"""
    template_name: str
    module_name: str
    variables: Dict[str, Any]
