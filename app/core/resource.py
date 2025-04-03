import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.models.resource import Resource, ResourceStatus
from app.models.environment import Environment
from app.core.exceptions import TerraformError, NotFoundError, BadRequestError

logger = get_logger("resource")


class ResourceService:
    """
    Service for managing Terraform resources within environments
    """

    def __init__(self, terraform_service: TerraformService):
        self.terraform_service = terraform_service
        self.running_tasks = {}

    def create_resource(
        self,
        db: Session,
        environment_id: str,
        name: str,
        module_path: str,
        resource_type: str,
        variables: Optional[Dict[str, Any]] = None,
        auto_apply: bool = True,
        correlation_id: Optional[str] = None,
    ) -> Resource:
        """
        Create a new resource record in the database

        Args:
            db: Database session
            environment_id: ID of the parent environment
            name: Resource name/identifier
            module_path: Path to Terraform module
            resource_type: Type of resource (e.g., ec2, s3)
            variables: Initial Terraform variables (can be updated at runtime)
            auto_apply: Whether to automatically apply after planning
            correlation_id: Correlation ID for request tracing

        Returns:
            Resource: The created resource object
        """
        # First, ensure the environment exists
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        if not environment:
            raise NotFoundError(f"Environment with ID {environment_id} not found")

        logger.info(
            f"Creating resource: {name}",
            environment_id=environment_id,
            name=name,
            module_path=module_path,
            resource_type=resource_type,
            auto_apply=auto_apply,
            correlation_id=correlation_id,
        )

        # Create the resource record
        resource = Resource(
            id=str(uuid.uuid4()),
            name=name,
            module_path=module_path,
            resource_type=resource_type,
            status=ResourceStatus.PENDING.value,
            variables=variables,
            correlation_id=correlation_id,
            auto_apply=str(auto_apply),
            environment_id=environment_id,
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        return resource

    def get_resource(self, db: Session, resource_id: str) -> Optional[Resource]:
        """
        Get a resource by ID

        Args:
            db: Database session
            resource_id: Resource ID

        Returns:
            Optional[Resource]: The resource if found, None otherwise
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
        List resources with optional filtering

        Args:
            db: Database session
            environment_id: Optional environment ID to filter by
            resource_type: Optional resource type to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Resource]: List of resources
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
        Update the status of a resource

        Args:
            db: Database session
            resource_id: Resource ID
            status: New status
            error_message: Optional error message

        Returns:
            Resource: The updated resource
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource not found: {resource_id}")

        resource.status = status.value
        if error_message:
            resource.error_message = error_message

        db.commit()
        db.refresh(resource)

        return resource

    def update_resource_execution(
        self, db: Session, resource_id: str, operation: TerraformOperation, execution_id: str
    ) -> Resource:
        """
        Update the execution ID for a specific operation

        Args:
            db: Database session
            resource_id: Resource ID
            operation: Terraform operation
            execution_id: Execution ID

        Returns:
            Resource: The updated resource
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource not found: {resource_id}")

        if operation == TerraformOperation.INIT:
            resource.init_execution_id = execution_id
        elif operation == TerraformOperation.PLAN:
            resource.plan_execution_id = execution_id
        elif operation == TerraformOperation.APPLY:
            resource.apply_execution_id = execution_id

        db.commit()
        db.refresh(resource)

        return resource

    def _get_backend_config(self, resource_id: str) -> Dict[str, str]:
        """
        Generate a backend configuration specific to this resource

        Args:
            resource_id: Resource ID

        Returns:
            Dict[str, str]: Backend configuration
        """
        # Each resource gets its own state file
        return {"path": f"terraform.{resource_id}.tfstate"}

    def _merge_variables(self, resource: Resource) -> Dict[str, Any]:
        """
        Merge environment global variables with resource-specific variables

        Args:
            resource: The resource object with relationship to environment

        Returns:
            Dict[str, Any]: Merged variables
        """
        # Start with global variables from the environment
        merged_vars = {}
        if resource.environment and resource.environment.global_variables:
            merged_vars.update(resource.environment.global_variables)
            
        # Override with resource-specific variables
        if resource.variables:
            merged_vars.update(resource.variables)
            
        return merged_vars

    async def run_terraform_init(
        self,
        db: Session,
        resource_id: str,
        variables: Optional[Dict[str, Any]] = None,
        force_init: bool = False,
    ) -> TerraformResult:
        """
        Run terraform init for a resource
        
        Instead of initializing at the resource level, this will now check if the environment
        has been initialized. If not, it will trigger environment-level initialization.
        
        This leverages the environment's Terraform backend configuration and module downloads.

        Args:
            db: Database session
            resource_id: Resource ID
            variables: Optional variables to override stored variables
            force_init: Whether to force initialization even if already initialized

        Returns:
            TerraformResult: Init operation result
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource not found: {resource_id}")

        # Use provided correlation ID or generate a new one
        correlation_id = resource.correlation_id or str(uuid.uuid4())

        # Update status to initializing
        self.update_resource_status(db, resource_id, ResourceStatus.INITIALIZING)

        try:
            # Check if environment is already initialized
            environment = resource.environment
            if not environment:
                raise BadRequestError(f"Resource {resource_id} is not associated with an environment")
            
            # Import the EnvironmentService here to avoid circular imports
            from app.core.environment import EnvironmentService
            env_service = EnvironmentService(self.terraform_service)
            
            # If environment is not initialized or force init is requested, initialize it
            if not environment.init_execution_id or force_init:
                logger.info(
                    "Initializing environment for resource",
                    resource_id=resource_id,
                    environment_id=environment.id,
                    correlation_id=correlation_id,
                )
                
                # Get merged variables
                merged_vars = self._merge_variables(resource)
                
                # Override with runtime variables if provided
                if variables:
                    merged_vars.update(variables)
                
                # Run terraform init at the environment level
                init_result = await env_service.run_terraform_init(
                    db=db,
                    environment_id=environment.id,
                    variables=merged_vars,
                )
                
                # If environment initialization was successful, we consider the resource initialized too
                if init_result.success:
                    self.update_resource_execution(
                        db, resource_id, TerraformOperation.INIT, init_result.execution_id
                    )
                    self.update_resource_status(db, resource_id, ResourceStatus.PENDING)
                else:
                    error_message = init_result.error or "Environment initialization failed"
                    logger.error(
                        f"Terraform init failed: {error_message}",
                        resource_id=resource_id,
                        environment_id=environment.id,
                        correlation_id=correlation_id,
                    )
                    self.update_resource_status(
                        db, resource_id, ResourceStatus.FAILED, error_message
                    )
                
                return init_result
            else:
                # Environment already initialized, just update the resource status and return success
                logger.info(
                    "Environment already initialized, skipping initialization",
                    resource_id=resource_id,
                    environment_id=environment.id,
                    correlation_id=correlation_id,
                )
                
                # Copy the environment's init execution ID to the resource
                self.update_resource_execution(
                    db, resource_id, TerraformOperation.INIT, environment.init_execution_id
                )
                self.update_resource_status(db, resource_id, ResourceStatus.PENDING)
                
                # Create a success result
                return TerraformResult(
                    operation=TerraformOperation.INIT,
                    success=True,
                    output="Environment already initialized, initialization skipped for resource",
                    duration_ms=0,
                    execution_id=environment.init_execution_id,
                )

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error during resource initialization: {error_message}",
                resource_id=resource_id,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_resource_status(db, resource_id, ResourceStatus.FAILED, error_message)
            raise

    async def run_terraform_plan(
        self,
        db: Session,
        resource_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> TerraformResult:
        """
        Run terraform plan for a resource

        This method will check if the resource's environment has been initialized.
        If not, it will first run initialization at the environment level.

        Args:
            db: Database session
            resource_id: Resource ID
            variables: Optional variables to override stored variables

        Returns:
            TerraformResult: Plan operation result
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource not found: {resource_id}")

        # Use provided correlation ID or generate a new one
        correlation_id = resource.correlation_id or str(uuid.uuid4())

        # Update status to planning
        self.update_resource_status(db, resource_id, ResourceStatus.PLANNING)

        try:
            # Make sure the environment has been initialized
            environment = resource.environment
            if not environment:
                raise BadRequestError(f"Resource {resource_id} is not associated with an environment")

            # Check if environment is initialized
            if not environment.init_execution_id or not resource.init_execution_id:
                logger.info(
                    "Initializing environment before planning",
                    resource_id=resource_id,
                    environment_id=environment.id,
                    correlation_id=correlation_id,
                )
                init_result = await self.run_terraform_init(db, resource_id, variables)
                if not init_result.success:
                    return init_result

            # Get merged variables
            merged_vars = self._merge_variables(resource)
            
            # Override with runtime variables if provided
            if variables:
                merged_vars.update(variables)

            # Run terraform plan
            plan_result = await self.terraform_service.plan(
                module_path=resource.module_path,
                variables=merged_vars,
                correlation_id=correlation_id,
            )

            # Update execution ID
            self.update_resource_execution(
                db, resource_id, TerraformOperation.PLAN, plan_result.execution_id
            )

            if not plan_result.success:
                error_message = plan_result.error or "Planning failed"
                logger.error(
                    f"Terraform plan failed: {error_message}",
                    resource_id=resource_id,
                    module_path=resource.module_path,
                    correlation_id=correlation_id,
                )
                self.update_resource_status(
                    db, resource_id, ResourceStatus.FAILED, error_message
                )
            else:
                # If plan succeeded and auto-apply is enabled, automatically run apply
                if resource.auto_apply == "True" and plan_result.has_changes:
                    logger.info(
                        "Auto-applying changes after successful plan",
                        resource_id=resource_id,
                        correlation_id=correlation_id,
                    )
                    # We'll use the existing task service to apply in the background
                    # This just schedules the apply, it doesn't wait for it
                    self.start_apply_task(db, resource_id, variables)
                else:
                    # Just update to pending if we're not auto-applying
                    self.update_resource_status(db, resource_id, ResourceStatus.PENDING)

            return plan_result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error during resource planning: {error_message}",
                resource_id=resource_id,
                module_path=resource.module_path if resource else "unknown",
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_resource_status(
                db, resource_id, ResourceStatus.FAILED, error_message
            )
            raise

    async def run_terraform_apply(
        self,
        db: Session,
        resource_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> TerraformResult:
        """
        Run terraform apply for a resource

        Args:
            db: Database session
            resource_id: Resource ID
            variables: Optional variables to override stored variables

        Returns:
            TerraformResult: Apply operation result
        """
        resource = self.get_resource(db, resource_id)
        if not resource:
            raise NotFoundError(f"Resource not found: {resource_id}")

        # Use provided correlation ID or generate a new one
        correlation_id = resource.correlation_id or str(uuid.uuid4())

        # Update status to applying
        self.update_resource_status(db, resource_id, ResourceStatus.APPLYING)

        try:
            # Make sure we have a valid plan first
            if not resource.plan_execution_id:
                logger.info(
                    "Planning resource before applying",
                    resource_id=resource_id,
                    correlation_id=correlation_id,
                )
                # Use the variables for planning if provided
                plan_result = await self.run_terraform_plan(db, resource_id, variables)
                if not plan_result.success:
                    return plan_result

            # Get merged variables
            merged_vars = self._merge_variables(resource)
            
            # Override with runtime variables if provided
            if variables:
                merged_vars.update(variables)

            # Run terraform apply
            apply_result = await self.terraform_service.apply(
                module_path=resource.module_path,
                variables=merged_vars,
                auto_approve=True,
                correlation_id=correlation_id,
            )

            # Update execution ID
            self.update_resource_execution(
                db, resource_id, TerraformOperation.APPLY, apply_result.execution_id
            )

            # Check if apply was successful
            if not apply_result.success:
                error_message = apply_result.error or "Apply failed"
                logger.error(
                    f"Terraform apply failed: {error_message}",
                    resource_id=resource_id,
                    module_path=resource.module_path,
                    correlation_id=correlation_id,
                )
                self.update_resource_status(
                    db, resource_id, ResourceStatus.FAILED, error_message
                )
            else:
                # Update status to provisioned
                self.update_resource_status(db, resource_id, ResourceStatus.PROVISIONED)

            return apply_result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error applying resource: {error_message}",
                resource_id=resource_id,
                module_path=resource.module_path,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_resource_status(
                db, resource_id, ResourceStatus.FAILED, error_message
            )
            raise 