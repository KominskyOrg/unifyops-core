# Pydantic schemas for request/response validation

from app.schemas.terraform import (
    # Base schemas
    OrganizationBase, 
    TeamBase,
    EnvironmentBase,
    ResourceBase,
    ConnectionBase,
    CloudCredentialBase,
    ComplianceRuleBase,
    DeploymentBase,
    
    # Create schemas
    OrganizationCreate,
    TeamCreate,
    EnvironmentCreate,
    ResourceCreate,
    ConnectionCreate,
    CloudCredentialCreate,
    ComplianceRuleCreate,
    DeploymentCreate,
    
    # Update schemas
    OrganizationUpdate,
    TeamUpdate,
    EnvironmentUpdate,
    ResourceUpdate,
    ConnectionUpdate,
    CloudCredentialUpdate,
    ComplianceRuleUpdate,
    
    # Response schemas
    OrganizationResponse,
    TeamResponse,
    ResourceResponse,
    ConnectionResponse,
    DeploymentResponse,
    EnvironmentResponse,
    EnvironmentDetailResponse,
    CloudCredentialResponse,
    ComplianceRuleResponse,
    
    # Special purpose schemas
    EnvironmentDeployRequest,
    EnvironmentResourcesRequest,
    DesignerStateRequest,
    DesignerStateResponse,
    ResourcePositionUpdate,
    GenerateTerraformRequest,
    DeployEnvironmentRequest,
    ApplyModuleRequest,
    TemplateVariableResponse,
    TemplateOutputResponse,
    TemplateDetailsResponse,
    CreateModuleFromTemplateRequest
)

# Export all schemas
__all__ = [
    # Base schemas
    "OrganizationBase", 
    "TeamBase",
    "EnvironmentBase",
    "ResourceBase",
    "ConnectionBase",
    "CloudCredentialBase",
    "ComplianceRuleBase",
    "DeploymentBase",
    
    # Create schemas
    "OrganizationCreate",
    "TeamCreate",
    "EnvironmentCreate",
    "ResourceCreate",
    "ConnectionCreate",
    "CloudCredentialCreate",
    "ComplianceRuleCreate",
    "DeploymentCreate",
    
    # Update schemas
    "OrganizationUpdate",
    "TeamUpdate",
    "EnvironmentUpdate",
    "ResourceUpdate",
    "ConnectionUpdate",
    "CloudCredentialUpdate",
    "ComplianceRuleUpdate",
    
    # Response schemas
    "OrganizationResponse",
    "TeamResponse",
    "ResourceResponse",
    "ConnectionResponse",
    "DeploymentResponse",
    "EnvironmentResponse",
    "EnvironmentDetailResponse",
    "CloudCredentialResponse",
    "ComplianceRuleResponse",
    
    # Special purpose schemas
    "EnvironmentDeployRequest",
    "EnvironmentResourcesRequest",
    "DesignerStateRequest",
    "DesignerStateResponse",
    "ResourcePositionUpdate",
    "GenerateTerraformRequest",
    "DeployEnvironmentRequest",
    "ApplyModuleRequest",
    "TemplateVariableResponse",
    "TemplateOutputResponse",
    "TemplateDetailsResponse",
    "CreateModuleFromTemplateRequest"
]
