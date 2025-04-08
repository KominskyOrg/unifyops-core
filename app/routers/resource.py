from fastapi import APIRouter, Depends, Request, status, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.resource import ResourceService
from app.core.exceptions import NotFoundError, BadRequestError, TerraformError, ErrorResponse
from app.core.logging import get_logger
from app.db.database import get_db
from app.dependencies import get_resource_service
from app.models.resource import ResourceStatus
from app.schemas.resource import (
    ResourceCreate,
    ResourceResponse,
    ResourceList,
    TerraformInitRequest,
    TerraformPlanRequest, 
    TerraformApplyRequest,
    TerraformInitResponse,
    TerraformPlanResponse,
    TerraformApplyResponse
)

# Create router with tags for documentation
router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resources"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Resource Not Found", "model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error",
            "model": ErrorResponse,
        },
    },
)

# Configure logger
logger = get_logger("resource.router")


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    request: Request,
    resource_data: ResourceCreate,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Create a new Terraform resource
    """
    try:
        # Get correlation ID from request headers if available
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Create the resource
        resource = resource_service.create_resource(
            db=db,
            environment_id=resource_data.environment_id,
            name=resource_data.name,
            module_path=resource_data.module_path,
            resource_type=resource_data.resource_type,
            variables=resource_data.variables,
            auto_apply=resource_data.auto_apply,
            correlation_id=correlation_id,
        )
        
        return ResourceResponse.model_validate(resource)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=ResourceList)
async def list_resources(
    request: Request,
    environment_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    List all resources, optionally filtered by environment ID or resource type
    """
    try:
        resources = resource_service.list_resources(
            db=db,
            environment_id=environment_id,
            resource_type=resource_type,
            skip=skip,
            limit=limit
        )
        
        return ResourceList(resources=resources, total=len(resources))
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    request: Request,
    resource_id: str,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Get details of a specific resource
    """
    try:
        resource = resource_service.get_resource(db=db, resource_id=resource_id)
        
        if not resource:
            raise NotFoundError(f"Resource with ID {resource_id} not found")
        
        return ResourceResponse.model_validate(resource)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{resource_id}/init", response_model=TerraformInitResponse)
async def init_resource(
    request: Request,
    resource_id: str,
    init_request: TerraformInitRequest,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Initialize a Terraform resource
    """
    try:
        # Get correlation ID from request headers if available
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Run init
        init_result = await resource_service.run_terraform_init(
            db=db, 
            resource_id=resource_id,
            variables=init_request.variables
        )
        
        return TerraformInitResponse(
            resource_id=resource_id,
            success=init_result.success,
            execution_id=init_result.execution_id,
            output=init_result.output,
            error=init_result.error,
            duration_ms=init_result.duration_ms
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TerraformError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{resource_id}/plan", response_model=TerraformPlanResponse)
async def plan_resource(
    request: Request,
    resource_id: str,
    plan_request: TerraformPlanRequest,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Plan a Terraform resource
    """
    try:
        # Get correlation ID from request headers if available
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Run plan
        plan_result = await resource_service.run_terraform_plan(
            db=db, 
            resource_id=resource_id,
            variables=plan_request.variables
        )
        
        return TerraformPlanResponse(
            resource_id=resource_id,
            success=plan_result.success,
            execution_id=plan_result.execution_id,
            plan_id=plan_result.plan_id,
            output=plan_result.output,
            error=plan_result.error,
            duration_ms=plan_result.duration_ms
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TerraformError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{resource_id}/apply", response_model=TerraformApplyResponse)
async def apply_resource(
    request: Request,
    resource_id: str,
    apply_request: TerraformApplyRequest,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Apply a Terraform resource
    """
    try:
        # Get correlation ID from request headers if available
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Run apply
        apply_result = await resource_service.run_terraform_apply(
            db=db, 
            resource_id=resource_id,
            variables=apply_request.variables
        )
        
        return TerraformApplyResponse(
            resource_id=resource_id,
            success=apply_result.success,
            execution_id=apply_result.execution_id,
            output=apply_result.output,
            error=apply_result.error,
            duration_ms=apply_result.duration_ms
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TerraformError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{resource_id}/provision",
    response_model=ResourceResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Provision a resource",
    description="""
    Triggers the provisioning process for a resource.
    This is an asynchronous operation that runs in the background.
    It will execute the full Terraform workflow (init, plan, and optionally apply).
    If the resource has auto_apply set to false, it will stop after the plan stage.
    """,
)
async def provision_resource(
    request: Request,
    resource_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    """
    Start provisioning a resource
    
    Args:
        request: The HTTP request
        resource_id: Resource ID
        background_tasks: FastAPI background tasks
        db: Database session
        resource_service: Resource service
        
    Returns:
        ResourceResponse: The resource with updated status
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        f"Starting resource provisioning: {resource_id}",
        resource_id=resource_id,
        correlation_id=correlation_id,
    )
    
    resource = resource_service.get_resource(db, resource_id)
    if not resource:
        raise NotFoundError(f"Resource not found: {resource_id}")
    
    # Check if resource is already being provisioned
    if resource.status in [
        ResourceStatus.INITIALIZING.value,
        ResourceStatus.PLANNING.value,
        ResourceStatus.APPLYING.value
    ]:
        return ResourceResponse.model_validate(resource)
    
    try:
        # Run init and plan in background
        background_tasks.add_task(
            resource_service.start_apply_task,
            db=db,
            resource_id=resource_id,
            variables=None,  # Use stored variables
        )
        
        # Update status to pending
        resource_service.update_resource_status(
            db, resource_id, ResourceStatus.PENDING
        )
        
        # Refresh resource
        resource = resource_service.get_resource(db, resource_id)
        
        return ResourceResponse.model_validate(resource)
        
    except Exception as e:
        logger.error(
            f"Error starting resource provisioning: {str(e)}",
            resource_id=resource_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) 