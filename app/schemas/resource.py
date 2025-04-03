from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class ResourceBase(BaseModel):
    """Base Resource schema with common attributes"""
    name: str = Field(..., description="Resource name")
    module_path: str = Field(..., description="Path to Terraform module")
    resource_type: str = Field(..., description="Type of resource (e.g., ec2, s3)")
    auto_apply: bool = Field(True, description="Whether to auto-apply after planning")
    variables: Optional[Dict[str, Any]] = Field(None, description="Terraform variables")


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource"""
    environment_id: str = Field(..., description="ID of the parent environment")


class ResourceResponse(ResourceBase):
    """Schema for resource response"""
    id: str = Field(..., description="Resource ID")
    environment_id: str = Field(..., description="ID of the parent environment")
    status: str = Field(..., description="Current status of the resource")
    error_message: Optional[str] = Field(None, description="Error message if any")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    init_execution_id: Optional[str] = Field(None, description="Latest init execution ID")
    plan_execution_id: Optional[str] = Field(None, description="Latest plan execution ID")
    apply_execution_id: Optional[str] = Field(None, description="Latest apply execution ID")

    class Config:
        from_attributes = True


class ResourceList(BaseModel):
    """Schema for listing resources"""
    resources: List[ResourceResponse] = Field(..., description="List of resources")
    total: int = Field(..., description="Total number of resources")


class TerraformInitRequest(BaseModel):
    """Schema for initializing a resource"""
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to use for initialization")


class TerraformPlanRequest(BaseModel):
    """Schema for planning a resource"""
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to use for planning")


class TerraformApplyRequest(BaseModel):
    """Schema for applying a resource"""
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to use for applying")


class TerraformInitResponse(BaseModel):
    """Schema for init operation response"""
    resource_id: str = Field(..., description="Resource ID")
    success: bool = Field(..., description="Whether the operation was successful")
    execution_id: str = Field(..., description="Execution ID")
    output: str = Field(..., description="Command output")
    error: Optional[str] = Field(None, description="Error message if any")
    duration_ms: int = Field(..., description="Duration in milliseconds")


class TerraformPlanResponse(BaseModel):
    """Schema for plan operation response"""
    resource_id: str = Field(..., description="Resource ID")
    success: bool = Field(..., description="Whether the operation was successful")
    execution_id: str = Field(..., description="Execution ID")
    plan_id: Optional[str] = Field(None, description="Plan ID for later application")
    output: str = Field(..., description="Command output")
    error: Optional[str] = Field(None, description="Error message if any")
    duration_ms: int = Field(..., description="Duration in milliseconds")


class TerraformApplyResponse(BaseModel):
    """Schema for apply operation response"""
    resource_id: str = Field(..., description="Resource ID")
    success: bool = Field(..., description="Whether the operation was successful")
    execution_id: str = Field(..., description="Execution ID")
    output: str = Field(..., description="Command output")
    error: Optional[str] = Field(None, description="Error message if any")
    duration_ms: int = Field(..., description="Duration in milliseconds") 