from fastapi import APIRouter, Depends, Request, status, HTTPException, BackgroundTasks, Response
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import os

from app.core.config import get_settings, Settings
from app.db.database import get_db
from app.core.environment import EnvironmentService
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.core.exceptions import TerraformError, BadRequestError, NotFoundError, ErrorResponse
from app.core.logging import get_logger
from app.schemas.environment import (
    EnvironmentCreate,
    EnvironmentResponse,
    EnvironmentListResponse,
    EnvironmentStatusResponse,
)
from app.models.environment import Environment, EnvironmentStatus
from app.schemas.terraform import (
    TerraformInitResponse,
    TerraformPlanResponse,
    TerraformApplyResponse,
)

# Create router with tags for documentation
router = APIRouter(
    prefix="/api/v1/environments",
    tags=["Environments"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Resource Not Found", "model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Terraform Operation Error",
            "model": ErrorResponse,
        },
    },
)
logger = get_logger("environment.router")

# Get the base directory for Terraform modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TF_DIR = os.path.join(BASE_DIR, "app/tf")

# Create Terraform service and Environment service
terraform_service = TerraformService(TF_DIR)
environment_service = EnvironmentService(terraform_service)


@router.post(
    "/",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Terraform environment",
    description="""
    Creates a new environment record to track Terraform operations.
    This endpoint only creates the database record and does not run any Terraform commands.
    Use the specific operation endpoints (/init, /plan, /apply) to perform Terraform operations
    on this environment.
    """,
)
async def create_environment(
    request: Request,
    environment_data: EnvironmentCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnvironmentResponse:
    """
    Create a new environment record
    
    Args:
        request: The HTTP request
        environment_data: Environment creation parameters
        db: Database session
        settings: Application settings
        
    Returns:
        EnvironmentResponse: The created environment with initial status
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        f"Creating environment: {environment_data.name}",
        name=environment_data.name,
        module_path=environment_data.module_path,
        correlation_id=correlation_id,
    )
    
    try:
        # Check if the module exists
        module_path = os.path.join(TF_DIR, environment_data.module_path)
        if not os.path.exists(module_path):
            raise NotFoundError(f"Module not found: {environment_data.module_path}")
            
        # Create the environment record in the database
        environment = environment_service.create_environment(
            db=db,
            name=environment_data.name,
            module_path=environment_data.module_path,
            variables=environment_data.variables,
            correlation_id=correlation_id,
        )
        
        return environment
        
    except Exception as e:
        # Log and re-raise the exception
        logger.error(
            f"Error creating environment: {str(e)}",
            name=environment_data.name,
            module_path=environment_data.module_path,
            exception=e,
            correlation_id=correlation_id,
        )
        raise


@router.get(
    "/{environment_id}",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get environment status",
    description="""
    Get the current status of a Terraform environment.
    This can be used to check the progress of a provisioning operation.
    """,
)
async def get_environment(
    request: Request,
    environment_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnvironmentResponse:
    """
    Get environment status

    Args:
        request: The HTTP request
        environment_id: Environment ID
        db: Database session
        settings: Application settings

    Returns:
        EnvironmentResponse: The environment with current status
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        f"Getting environment status: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )

    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")

    return environment


@router.get(
    "/",
    response_model=EnvironmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all environments",
    description="""
    List all Terraform environments with their current status.
    """,
)
async def list_environments(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnvironmentListResponse:
    """
    List all environments

    Args:
        request: The HTTP request
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        settings: Application settings

    Returns:
        EnvironmentListResponse: List of environments
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        "Listing environments",
        skip=skip,
        limit=limit,
        correlation_id=correlation_id,
    )

    environments = environment_service.list_environments(db, skip, limit)

    return {
        "environments": environments,
        "count": len(environments),
    }


@router.post(
    "/{environment_id}/init",
    response_model=TerraformInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize an environment",
    description="""
    Initialize a Terraform environment by running `terraform init`.
    This operation is synchronous and will return when init completes.
    """,
)
async def init_environment(
    request: Request,
    environment_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TerraformInitResponse:
    """
    Initialize a Terraform environment

    Args:
        request: The HTTP request
        environment_id: Environment ID
        db: Database session
        settings: Application settings

    Returns:
        TerraformInitResponse: The result of the init operation
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        f"Initializing environment: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )

    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")

    try:
        # Run terraform init synchronously
        init_result = await environment_service.run_terraform_init(db, environment_id)

        # Convert to API response
        return TerraformInitResponse(
            operation=init_result.operation.value,
            success=init_result.success,
            message="Terraform module initialized successfully"
            if init_result.success
            else init_result.error or "Initialization failed",
            execution_id=init_result.execution_id,
            duration_ms=init_result.duration_ms,
        )

    except Exception as e:
        logger.error(
            f"Error initializing environment: {str(e)}",
            environment_id=environment_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise TerraformError(str(e))


@router.post(
    "/{environment_id}/plan",
    response_model=TerraformPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan an environment",
    description="""
    Create a Terraform execution plan for an environment.
    This operation is synchronous and will return when plan completes.
    """,
)
async def plan_environment(
    request: Request,
    environment_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TerraformPlanResponse:
    """
    Plan a Terraform environment

    Args:
        request: The HTTP request
        environment_id: Environment ID
        db: Database session
        settings: Application settings

    Returns:
        TerraformPlanResponse: The result of the plan operation
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        f"Planning environment: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )

    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")

    try:
        # Run terraform plan synchronously
        plan_result = await environment_service.run_terraform_plan(db, environment_id)

        # Convert to API response
        return TerraformPlanResponse(
            operation=plan_result.operation.value,
            success=plan_result.success,
            message="Terraform plan created successfully"
            if plan_result.success
            else plan_result.error or "Planning failed",
            execution_id=plan_result.execution_id,
            duration_ms=plan_result.duration_ms,
            plan_id=plan_result.execution_id,
        )

    except Exception as e:
        logger.error(
            f"Error planning environment: {str(e)}",
            environment_id=environment_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise TerraformError(str(e))


@router.post(
    "/{environment_id}/apply",
    response_model=TerraformApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply an environment",
    description="""
    Apply a Terraform execution plan for an environment.
    This operation is synchronous and will return when apply completes.
    """,
)
async def apply_environment(
    request: Request,
    environment_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TerraformApplyResponse:
    """
    Apply a Terraform environment

    Args:
        request: The HTTP request
        environment_id: Environment ID
        db: Database session
        settings: Application settings

    Returns:
        TerraformApplyResponse: The result of the apply operation
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        f"Applying environment: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )

    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")

    try:
        # Run terraform apply synchronously
        apply_result = await environment_service.run_terraform_apply(db, environment_id)

        # Convert to API response
        return TerraformApplyResponse(
            operation=apply_result.operation.value,
            success=apply_result.success,
            message="Terraform apply completed successfully"
            if apply_result.success
            else apply_result.error or "Apply failed",
            execution_id=apply_result.execution_id,
            duration_ms=apply_result.duration_ms,
            outputs=apply_result.outputs or {},
        )

    except Exception as e:
        logger.error(
            f"Error applying environment: {str(e)}",
            environment_id=environment_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise TerraformError(str(e))


@router.post(
    "/{environment_id}/provision",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Provision an environment",
    description="""
    Triggers the provisioning process for an existing environment.
    This is an asynchronous operation that runs in the background.
    It will execute the full Terraform workflow (init, plan, and optionally apply).
    If the environment has auto_apply set to false, it will stop after the plan stage.
    """,
)
async def provision_environment(
    request: Request,
    environment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnvironmentResponse:
    """
    Start provisioning an environment
    
    Args:
        request: The HTTP request
        environment_id: Environment ID
        background_tasks: FastAPI background tasks
        db: Database session
        settings: Application settings
        
    Returns:
        EnvironmentResponse: The environment with updated status
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        f"Starting environment provisioning: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )
    
    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")
    
    # Check if environment is already being provisioned
    if environment.status in [
        EnvironmentStatus.INITIALIZING.value,
        EnvironmentStatus.PLANNING.value,
        EnvironmentStatus.APPLYING.value
    ]:
        return environment
    
    try:
        # Start the provisioning in the background
        background_tasks.add_task(
            environment_service.start_provisioning_task,
            db=db,
            environment_id=environment_id,
        )
        
        # Update status to pending
        environment_service.update_environment_status(
            db, environment_id, EnvironmentStatus.PENDING
        )
        
        # Refresh environment
        environment = environment_service.get_environment(db, environment_id)
        
        return environment
        
    except Exception as e:
        logger.error(
            f"Error starting environment provisioning: {str(e)}",
            environment_id=environment_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise


@router.get(
    "/{environment_id}/status",
    response_model=EnvironmentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed environment status",
    description="""
    Get detailed status information for a Terraform environment.
    This endpoint provides comprehensive information about the current state
    of the environment, including execution IDs, resource counts, and outputs
    when available.
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "Detailed environment status",
            "model": EnvironmentStatusResponse
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Environment not found",
            "model": ErrorResponse
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Error retrieving environment status",
            "model": ErrorResponse
        }
    }
)
async def get_environment_status(
    request: Request,
    environment_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnvironmentStatusResponse:
    """
    Get detailed environment status
    
    Args:
        request: The HTTP request
        environment_id: Environment ID
        db: Database session
        settings: Application settings
        
    Returns:
        EnvironmentStatusResponse: Detailed environment status
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        f"Getting detailed environment status: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )
    
    try:
        # Get detailed status
        status_info = environment_service.get_environment_status(
            db, environment_id, correlation_id=correlation_id
        )
        
        logger.debug(
            f"Retrieved environment status: {environment_id}",
            environment_id=environment_id,
            status=status_info.get("status"),
            correlation_id=correlation_id,
        )
        
        return status_info
        
    except NotFoundError as e:
        logger.warning(
            f"Environment not found: {environment_id}",
            environment_id=environment_id,
            correlation_id=correlation_id,
        )
        raise
        
    except Exception as e:
        logger.error(
            f"Error retrieving environment status: {str(e)}",
            environment_id=environment_id,
            exception=e,
            correlation_id=correlation_id,
        )
        raise TerraformError(f"Failed to retrieve environment status: {str(e)}")


@router.delete(
    "/{environment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an environment",
    description="""
    Delete a Terraform environment and all its associated infrastructure.
    This operation will first run `terraform destroy` to remove all provisioned resources,
    then delete the environment record from the database.
    """,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Environment deleted successfully"},
        status.HTTP_404_NOT_FOUND: {
            "description": "Environment not found",
            "model": ErrorResponse
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid operation",
            "model": ErrorResponse
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Error during deletion",
            "model": ErrorResponse
        }
    }
)
async def delete_environment(
    request: Request,
    environment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Delete an environment and all its associated infrastructure
    
    Args:
        request: The HTTP request
        environment_id: Environment ID
        background_tasks: Background tasks
        db: Database session
        settings: Application settings
        
    Returns:
        None: 204 No Content response
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        f"Deleting environment: {environment_id}",
        environment_id=environment_id,
        correlation_id=correlation_id,
    )
    
    # Check if the environment exists
    environment = environment_service.get_environment(db, environment_id)
    if not environment:
        raise NotFoundError(f"Environment not found: {environment_id}")
        
    # Add the delete operation as a background task
    background_tasks.add_task(
        environment_service.delete_environment,
        db=db,
        environment_id=environment_id,
        correlation_id=correlation_id,
    )
    
    # Return 204 No Content
    return Response(status_code=status.HTTP_204_NO_CONTENT)
