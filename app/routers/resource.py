from fastapi import APIRouter, Depends, Request, status, HTTPException, BackgroundTasks, Response
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.resource import ResourceService
from app.core.exceptions import NotFoundError, BadRequestError, ErrorResponse
from app.core.logging import get_logger
from app.db.database import get_db
from app.dependencies import get_resource_service
from app.models.resource import ResourceStatus
from app.schemas.resource import (
    ResourceCreate,
    ResourceResponse,
    ResourceList,
)

# Create router with tags for documentation
router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resource Definitions"],
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
    Create a new resource definition to be included in an environment.
    This only creates the definition, it does not provision the infrastructure.
    """
    try:
        correlation_id = request.headers.get("X-Correlation-ID")
        resource = resource_service.create_resource(
            db=db,
            environment_id=resource_data.environment_id,
            name=resource_data.name,
            resource_type=resource_data.resource_type,
            variables=resource_data.variables,
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
    List all resource definitions, optionally filtered by environment ID or resource type.
    """
    try:
        resources = resource_service.list_resources(
            db=db,
            environment_id=environment_id,
            resource_type=resource_type,
            skip=skip,
            limit=limit
        )
        return ResourceList(resources=[ResourceResponse.model_validate(r) for r in resources], total=len(resources))
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
    Get details of a specific resource definition.
    """
    try:
        resource = resource_service.get_resource(db=db, resource_id=resource_id)
        if not resource:
            raise NotFoundError(f"Resource definition with ID {resource_id} not found")
        return ResourceResponse.model_validate(resource)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    request: Request,
    resource_id: str,
    resource_update: ResourceCreate,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Update an existing resource definition.
    Note: This modifies the definition. To apply changes, re-provision the environment.
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    logger.info(f"Updating resource definition {resource_id}", resource_id=resource_id, correlation_id=correlation_id)
    
    resource = resource_service.get_resource(db, resource_id)
    if not resource:
        raise NotFoundError(f"Resource definition with ID {resource_id} not found")

    resource.name = resource_update.name
    resource.resource_type = resource_update.resource_type
    resource.variables = resource_update.variables
    if resource.environment_id != resource_update.environment_id:
        new_env = db.query(Environment).filter(Environment.id == resource_update.environment_id).first()
        if not new_env:
            raise BadRequestError(f"Cannot move resource definition: New environment {resource_update.environment_id} not found")
        resource.environment_id = resource_update.environment_id
        logger.info(f"Moved resource definition {resource_id} to environment {resource.environment_id}", resource_id=resource_id)
        
    resource.status = ResourceStatus.PENDING.value
    resource.error_message = None
    
    try:
        db.commit()
        db.refresh(resource)
        logger.info(f"Successfully updated resource definition {resource_id}", resource_id=resource_id)
        return ResourceResponse.model_validate(resource)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating resource definition {resource_id}: {e}", resource_id=resource_id, exception=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update resource definition: {str(e)}")


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    request: Request,
    resource_id: str,
    db: Session = Depends(get_db),
    resource_service: ResourceService = Depends(get_resource_service),
):
    """
    Delete a resource definition.
    Note: This removes the definition. To remove the infrastructure, re-provision the environment.
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    logger.info(f"Deleting resource definition {resource_id}", resource_id=resource_id, correlation_id=correlation_id)
    
    resource = resource_service.get_resource(db, resource_id)
    if not resource:
        raise NotFoundError(f"Resource definition with ID {resource_id} not found")
        
    try:
        db.delete(resource)
        db.commit()
        logger.info(f"Successfully deleted resource definition {resource_id}", resource_id=resource_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting resource definition {resource_id}: {e}", resource_id=resource_id, exception=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete resource definition: {str(e)}") 