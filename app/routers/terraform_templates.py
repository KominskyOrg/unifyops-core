from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, status, Query, Path, Request
from pydantic import BaseModel

from app.core.terraform_templates import TemplateManager
from app.logging.context import get_logger
from app.exceptions import (
    ResourceNotFoundError,
    BadRequestError,
    TerraformError
)
from app.exceptions.utils import error_context

router = APIRouter(
    prefix="/terraform/templates",
    tags=["terraform-templates"],
    responses={404: {"description": "Not found"}},
)

logger = get_logger("api.terraform.templates", metadata={"router": "terraform.templates"})


class TemplateBasicInfo(BaseModel):
    """Basic template information model"""
    id: str
    name: str
    description: str
    category: str
    provider: str


class TemplateVariableInfo(BaseModel):
    """Template variable information model"""
    name: str
    description: str
    type: str
    default: Optional[str] = None
    required: bool


class TemplateOutputInfo(BaseModel):
    """Template output information model"""
    name: str
    description: str
    sensitive: Optional[bool] = False


class TemplateDetailedInfo(TemplateBasicInfo):
    """Detailed template information model"""
    variables: List[TemplateVariableInfo]
    outputs: List[TemplateOutputInfo]


class CreateModuleRequest(BaseModel):
    """Request model for creating a module from a template"""
    template_id: str
    target_path: str
    variables: Optional[Dict[str, str]] = None


class CreateModuleResponse(BaseModel):
    """Response model for module creation"""
    module_path: str
    template_id: str


@router.get("/", response_model=List[TemplateBasicInfo])
async def list_templates(
    request: Request,
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    List available Terraform module templates with optional filtering
    """
    with error_context(provider=provider, category=category, operation="list_templates"):
        template_manager: TemplateManager = request.app.state.template_manager
        templates = template_manager.get_available_templates()
        
        # Apply filters if provided
        if provider:
            templates = [t for t in templates if t["provider"] == provider]
        
        if category:
            templates = [t for t in templates if t["category"] == category]
        
        return templates


@router.get("/{template_id}", response_model=TemplateDetailedInfo)
async def get_template_details(
    request: Request,
    template_id: str = Path(..., description="Template identifier"),
):
    """
    Get detailed information about a specific template
    """
    with error_context(template_id=template_id, operation="get_template_details"):
        template_manager: TemplateManager = request.app.state.template_manager
        
        try:
            return template_manager.get_template_details(template_id)
        except ValueError as e:
            raise ResourceNotFoundError(
                resource_type="Template",
                resource_id=template_id,
                message=str(e)
            )


@router.post("/create-module", response_model=CreateModuleResponse)
async def create_module_from_template(
    request: Request,
    create_request: CreateModuleRequest,
):
    """
    Create a new Terraform module from a template
    """
    with error_context(
        template_id=create_request.template_id,
        target_path=create_request.target_path,
        operation="create_module_from_template"
    ):
        template_manager: TemplateManager = request.app.state.template_manager
        
        try:
            module_path = template_manager.create_module_from_template(
                template_id=create_request.template_id,
                target_path=create_request.target_path,
                variables=create_request.variables
            )
            
            return CreateModuleResponse(
                module_path=module_path,
                template_id=create_request.template_id
            )
        except ValueError as e:
            raise BadRequestError(
                message=f"Failed to create module: {str(e)}",
                parameter="template_id" if "template not found" in str(e).lower() else "target_path"
            )
        except Exception as e:
            logger.error(f"Error creating module from template: {str(e)}")
            raise TerraformError(
                message=f"Error creating module: {str(e)}",
                operation="create_module_from_template"
            ) 