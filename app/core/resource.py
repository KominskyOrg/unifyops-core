import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.logging import get_logger, get_background_task_logger
from app.models.resource import Resource, ResourceStatus
from app.models.environment import Environment
from app.core.exceptions import NotFoundError, BadRequestError

logger = get_logger("resource")


class ResourceService:
    """
    Service for managing Terraform resource definitions within environments.
    This service handles CRUD operations for resources and does NOT execute Terraform commands.
    """

    def __init__(self):
        # No Terraform service needed here anymore
        pass

    def create_resource(
        self,
        db: Session,
        environment_id: str,
        name: str,
        resource_type: str,
        variables: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Resource:
        """
        Create a new resource definition record in the database.
        The actual infrastructure is managed at the Environment level.

        Args:
            db: Database session
            environment_id: ID of the parent environment
            name: Resource definition name/identifier
            resource_type: Type of resource definition (e.g., ec2_instance, s3_bucket)
            variables: Terraform variables specific to this resource definition
            correlation_id: Correlation ID for request tracing

        Returns:
            Resource: The created resource definition object
        """
        # First, ensure the environment exists
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        if not environment:
            raise NotFoundError(f"Environment with ID {environment_id} not found")

        logger.info(
            f"Creating resource definition: {name}",
            environment_id=environment_id,
            name=name,
            resource_type=resource_type,
            correlation_id=correlation_id,
        )

        # Create the resource record
        resource = Resource(
            id=str(uuid.uuid4()),
            name=name,
            resource_type=resource_type,
            status=ResourceStatus.PENDING.value,
            variables=variables,
            correlation_id=correlation_id,
            environment_id=environment_id,
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        return resource

    def get_resource(self, db: Session, resource_id: str) -> Optional[Resource]:
        """
        Get a resource definition by ID

        Args:
            db: Database session
            resource_id: Resource ID

        Returns:
            Optional[Resource]: The resource definition if found, None otherwise
        """
        return db.query(Resource).filter(Resource.id == resource_id).first()

    def list_resources(
        self, 
        db: Session, 
        environment_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Resource]:
        """
        List resource definitions with optional filtering

        Args:
            db: Database session
            environment_id: Optional environment ID to filter by
            resource_type: Optional resource type to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Resource]: List of resource definitions
        """
        query = db.query(Resource)
        
        if environment_id:
            query = query.filter(Resource.environment_id == environment_id)
            
        if resource_type:
            query = query.filter(Resource.resource_type == resource_type)
            
        return query.order_by(Resource.created_at.desc()).offset(skip).limit(limit).all()

    def update_resource_status(
        self,
        db: Session,
        resource_id: str,
        status: ResourceStatus,
        error_message: Optional[str] = None,
    ) -> Resource:
        """
        Update the status of a resource definition (e.g., PENDING, ACTIVE, INVALID)

        Args:
            db: Database session
            resource_id: Resource ID
            status: New status for the definition
            error_message: Optional error message related to the definition

        Returns:
            Resource: The updated resource definition
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource definition not found: {resource_id}")

        resource.status = status.value
        if error_message:
            resource.error_message = error_message
        else:
            # Clear error message if status is not FAILED/INVALID
            if status != ResourceStatus.FAILED: 
                 resource.error_message = None

        db.commit()
        db.refresh(resource)

        return resource

    # Remove update_resource_execution as it relates to Terraform runs
    # def update_resource_execution(...)

    # Remove _get_backend_config as backend is environment-specific
    # def _get_backend_config(...)
    
    # Remove _merge_variables, this logic will move to EnvironmentService
    # def _merge_variables(...)

    # Remove run_terraform_init
    # async def run_terraform_init(...)

    # Remove run_terraform_plan
    # async def run_terraform_plan(...)

    # Remove start_apply_task
    # def start_apply_task(...)

    # Remove provision_resource
    # async def provision_resource(...)

    # Remove run_terraform_apply
    # async def run_terraform_apply(...) 