import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.models.environment import Environment, EnvironmentStatus
from app.core.exceptions import TerraformError, NotFoundError, BadRequestError

logger = get_logger("environment")


class EnvironmentService:
    """
    Service for managing Terraform environments with background tasks
    """

    def __init__(self, terraform_service: TerraformService):
        self.terraform_service = terraform_service
        self.running_tasks = {}

    def create_environment(
        self,
        db: Session,
        name: str,
        module_path: str,
        resource_name: str,
        variables: Optional[Dict[str, Any]] = None,
        auto_apply: bool = True,
        correlation_id: Optional[str] = None,
    ) -> Environment:
        """
        Create a new environment record in the database

        Args:
            db: Database session
            name: Environment name (e.g., dev, staging, prod)
            module_path: Path to Terraform module
            resource_name: Name of the resource being managed
            variables: Optional initial Terraform variables (can be provided later)
            auto_apply: Whether to automatically apply after planning
            correlation_id: Correlation ID for request tracing

        Returns:
            Environment: The created environment object
        """
        logger.info(
            f"Creating environment: {name}",
            name=name,
            module_path=module_path,
            resource_name=resource_name,
            auto_apply=auto_apply,
            correlation_id=correlation_id,
        )

        # Create the environment record
        environment = Environment(
            id=str(uuid.uuid4()),
            name=name,
            module_path=module_path,
            resource_name=resource_name,
            status=EnvironmentStatus.PENDING.value,
            variables=variables,  # Can be None, variables provided at runtime
            correlation_id=correlation_id,
            auto_apply=str(auto_apply),
        )

        db.add(environment)
        db.commit()
        db.refresh(environment)

        return environment

    def get_environment(self, db: Session, environment_id: str) -> Optional[Environment]:
        """
        Get an environment by ID

        Args:
            db: Database session
            environment_id: Environment ID

        Returns:
            Optional[Environment]: The environment if found, None otherwise
        """
        return db.query(Environment).filter(Environment.id == environment_id).first()

    def list_environments(self, db: Session, skip: int = 0, limit: int = 100) -> List[Environment]:
        """
        List all environments

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Environment]: List of environments
        """
        return (
            db.query(Environment)
            .order_by(Environment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_environment_status(
        self,
        db: Session,
        environment_id: str,
        status: EnvironmentStatus,
        error_message: Optional[str] = None,
    ) -> Environment:
        """
        Update the status of an environment

        Args:
            db: Database session
            environment_id: Environment ID
            status: New status
            error_message: Optional error message

        Returns:
            Environment: The updated environment
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        environment.status = status.value
        if error_message:
            environment.error_message = error_message

        db.commit()
        db.refresh(environment)

        return environment

    def update_environment_execution(
        self, db: Session, environment_id: str, operation: TerraformOperation, execution_id: str
    ) -> Environment:
        """
        Update the execution ID for a specific operation

        Args:
            db: Database session
            environment_id: Environment ID
            operation: Terraform operation
            execution_id: Execution ID

        Returns:
            Environment: The updated environment
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        if operation == TerraformOperation.INIT:
            environment.init_execution_id = execution_id
        elif operation == TerraformOperation.PLAN:
            environment.plan_execution_id = execution_id
        elif operation == TerraformOperation.APPLY:
            environment.apply_execution_id = execution_id

        db.commit()
        db.refresh(environment)

        return environment

    def _get_backend_config(self, environment_id: str) -> Dict[str, str]:
        """
        Generate a backend configuration specific to this environment

        Args:
            environment_id: Environment ID

        Returns:
            Dict[str, str]: Backend configuration
        """
        # This is an example using a local backend to isolate state per environment
        # In production, you'd likely use a remote backend (S3, Azure, etc.)
        # with environment-specific key paths

        return {"path": f"terraform.{environment_id}.tfstate"}

    async def run_terraform_init(
        self,
        db: Session,
        environment_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> TerraformResult:
        """
        Run terraform init for an environment
        
        This initializes Terraform at the environment level, which will manage the overall
        Terraform backend configuration and module downloads.
        Resources within this environment will use this initialization rather than
        having their own separate initialization.

        Args:
            db: Database session
            environment_id: Environment ID
            variables: Optional variables to override stored variables

        Returns:
            TerraformResult: Init operation result
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        # Use provided correlation ID or generate a new one
        correlation_id = environment.correlation_id or str(uuid.uuid4())

        # Update status to initializing
        self.update_environment_status(db, environment_id, EnvironmentStatus.INITIALIZING)

        try:
            # Get environment-specific backend config
            backend_config = self._get_backend_config(environment_id)
            
            # Get merged variables - apply user-provided variables if available
            merged_vars = environment.variables or {}
            if variables:
                merged_vars.update(variables)

            # Run terraform init
            init_result = await self.terraform_service.init(
                module_path=environment.module_path,
                backend_config=backend_config,
                correlation_id=correlation_id,
            )

            # Update execution ID
            self.update_environment_execution(
                db, environment_id, TerraformOperation.INIT, init_result.execution_id
            )

            # Check if init was successful
            if not init_result.success:
                error_message = init_result.error or "Initialization failed"
                logger.error(
                    f"Terraform init failed: {error_message}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                # Only update status if we just did init by itself
                self.update_environment_status(db, environment_id, EnvironmentStatus.PENDING)

            return init_result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error initializing environment: {error_message}",
                environment_id=environment_id,
                module_path=environment.module_path,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_environment_status(
                db, environment_id, EnvironmentStatus.FAILED, error_message
            )
            raise

    async def run_terraform_plan(
        self,
        db: Session,
        environment_id: str,
    ) -> TerraformResult:
        """
        Run Terraform plan for an environment

        Args:
            db: Database session
            environment_id: ID of the environment to plan

        Returns:
            TerraformResult: The result of the plan operation
        """
        # Get the environment
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment with ID {environment_id} not found")

        # Check if environment is in a valid state for planning
        if environment.status in [EnvironmentStatus.APPLYING.value, EnvironmentStatus.DESTROYING.value]:
            raise BadRequestError(f"Environment is currently {environment.status}, cannot plan")

        # Generate a correlation ID for this operation
        correlation_id = str(uuid.uuid4())

        # Update status to indicate planning is in progress
        self.update_environment_status(db, environment_id, EnvironmentStatus.PLANNING)

        logger = get_logger("environment.terraform")
        logger.info(
            "Planning environment",
            environment_id=environment_id,
            module_path=environment.module_path,
            correlation_id=correlation_id,
        )

        try:
            # Make sure we have a valid init first
            if not environment.init_execution_id:
                logger.info(
                    "Initializing environment before planning",
                    environment_id=environment_id,
                    correlation_id=correlation_id,
                )
                init_result = await self.run_terraform_init(db, environment_id)
                if not init_result.success:
                    return init_result

            # Get backend config for state management
            backend_config = self._get_backend_config(environment_id)
            
            # Note: backend_config is not used for plan operation, only init
            # It was incorrectly being passed to plan() which doesn't accept it

            # Run terraform plan
            plan_result = await self.terraform_service.plan(
                module_path=environment.module_path,
                variables=environment.variables,
                correlation_id=correlation_id,
            )

            # Update execution ID
            self.update_environment_execution(
                db, environment_id, TerraformOperation.PLAN, plan_result.execution_id
            )

            # Check if plan was successful
            if not plan_result.success:
                error_message = plan_result.error or "Planning failed"
                logger.error(
                    f"Terraform plan failed: {error_message}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                # Update status based on whether we'll be applying
                if environment.auto_apply == "True":
                    # Will be applying next, so leave status as is
                    pass
                else:
                    # Just planning, mark as planned
                    self.update_environment_status(db, environment_id, EnvironmentStatus.PLANNING)

            return plan_result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error planning environment: {error_message}",
                environment_id=environment_id,
                module_path=environment.module_path,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_environment_status(
                db, environment_id, EnvironmentStatus.FAILED, error_message
            )
            raise

    async def run_terraform_apply(
        self,
        db: Session,
        environment_id: str,
    ) -> TerraformResult:
        """
        Run terraform apply for an environment

        Args:
            db: Session
            environment_id: Environment ID

        Returns:
            TerraformResult: Apply operation result
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        correlation_id = environment.correlation_id

        # Update status to applying
        self.update_environment_status(db, environment_id, EnvironmentStatus.APPLYING)

        try:
            # Make sure we have a valid plan first
            if not environment.plan_execution_id:
                logger.info(
                    "Planning environment before applying",
                    environment_id=environment_id,
                    correlation_id=correlation_id,
                )
                plan_result = await self.run_terraform_plan(db, environment_id)
                if not plan_result.success:
                    return plan_result

            # Get backend config for state management
            backend_config = self._get_backend_config(environment_id)

            # Run terraform apply
            apply_result = await self.terraform_service.apply(
                module_path=environment.module_path,
                variables=environment.variables,
                backend_config=backend_config,
                auto_approve=True,
                correlation_id=correlation_id,
            )

            # Update execution ID
            self.update_environment_execution(
                db, environment_id, TerraformOperation.APPLY, apply_result.execution_id
            )

            # Check if apply was successful
            if not apply_result.success:
                error_message = apply_result.error or "Apply failed"
                logger.error(
                    f"Terraform apply failed: {error_message}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                # Update status to provisioned
                self.update_environment_status(db, environment_id, EnvironmentStatus.PROVISIONED)

            return apply_result

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error applying environment: {error_message}",
                environment_id=environment_id,
                module_path=environment.module_path,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_environment_status(
                db, environment_id, EnvironmentStatus.FAILED, error_message
            )
            raise

    async def provision_environment(
        self,
        db: Session,
        environment_id: str,
    ):
        """
        Asynchronously provision an environment using Terraform

        Args:
            db: Database session
            environment_id: Environment ID
        """
        # Get environment from database
        environment = self.get_environment(db, environment_id)
        if not environment:
            logger.error(f"Environment not found: {environment_id}")
            return

        correlation_id = environment.correlation_id

        logger.info(
            f"Starting provisioning of environment: {environment.name}",
            environment_id=environment_id,
            module_path=environment.module_path,
            auto_apply=environment.auto_apply,
            correlation_id=correlation_id,
        )

        try:
            # Run terraform init
            init_result = await self.run_terraform_init(db, environment_id)
            if not init_result.success:
                return

            # Run terraform plan
            plan_result = await self.run_terraform_plan(db, environment_id)
            if not plan_result.success:
                return

            # Check if we should apply
            if environment.auto_apply == "True":
                # Run terraform apply
                apply_result = await self.run_terraform_apply(db, environment_id)
                if not apply_result.success:
                    return

                logger.info(
                    f"Environment provisioned successfully: {environment.name}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
            else:
                logger.info(
                    f"Environment planned successfully (apply skipped): {environment.name}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )

                # Update final status to "PLANNING" when auto_apply is False
                self.update_environment_status(db, environment_id, EnvironmentStatus.PLANNING)

        except Exception as e:
            logger.error(
                f"Error provisioning environment: {str(e)}",
                environment_id=environment_id,
                module_path=environment.module_path,
                exception=e,
                correlation_id=correlation_id,
            )
            self.update_environment_status(db, environment_id, EnvironmentStatus.FAILED, str(e))

        finally:
            # Remove from running tasks
            if environment_id in self.running_tasks:
                del self.running_tasks[environment_id]

    def start_provisioning_task(self, db: Session, environment_id: str):
        """
        Start a background task to provision an environment

        Args:
            db: Database session
            environment_id: Environment ID
        """
        # Create the task
        task = asyncio.create_task(self.provision_environment(db, environment_id))

        # Store the task
        self.running_tasks[environment_id] = task

        # Return the environment ID
        return environment_id

    def get_environment_status(
        self, 
        db: Session, 
        environment_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed status information for an environment
        
        Args:
            db: Database session
            environment_id: Environment ID
            correlation_id: Correlation ID for request tracing
            
        Returns:
            Dict[str, Any]: Detailed status information
        """
        # Get the environment
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")
        
        # Basic status info from the environment record
        status_info = {
            "id": environment.id,
            "name": environment.name,
            "status": environment.status,
            "init_execution_id": environment.init_execution_id,
            "plan_execution_id": environment.plan_execution_id,
            "apply_execution_id": environment.apply_execution_id,
            "created_at": environment.created_at,
            "updated_at": environment.updated_at,
            "error_message": environment.error_message,
        }
        
        try:
            # Add state file information
            state_file = f"terraform.{environment_id}.tfstate"
            state_path = os.path.join(
                self.terraform_service.base_dir, 
                environment.module_path, 
                state_file
            )
            
            if os.path.exists(state_path):
                status_info["state_file"] = state_file
                
                # Read state file to get resource count and outputs
                try:
                    with open(state_path, 'r') as f:
                        import json
                        state_data = json.load(f)
                        
                        # Extract resource count if available
                        if "resources" in state_data:
                            status_info["resource_count"] = len(state_data["resources"])
                        
                        # Extract outputs if available
                        if "outputs" in state_data:
                            status_info["outputs"] = {
                                k: v.get("value") for k, v in state_data["outputs"].items()
                            }
                except Exception as e:
                    logger.warning(
                        f"Error reading state file: {str(e)}",
                        environment_id=environment_id,
                        state_file=state_path,
                        exception=e,
                        correlation_id=correlation_id,
                    )
            
            # If environment is provisioned but we couldn't get outputs from state file,
            # try to get them directly from Terraform
            if (environment.status == EnvironmentStatus.PROVISIONED.value and
                    environment.apply_execution_id and
                    "outputs" not in status_info):
                try:
                    # Create a background function to call output
                    async def get_outputs():
                        return await self.terraform_service.output(
                            module_path=environment.module_path,
                            backend_config=self._get_backend_config(environment_id),
                            correlation_id=correlation_id,
                        )
                    
                    # Run the function to get outputs
                    import asyncio
                    output_result = asyncio.run(get_outputs())
                    
                    if output_result.success and output_result.outputs:
                        status_info["outputs"] = output_result.outputs
                
                except Exception as e:
                    logger.warning(
                        f"Error getting outputs: {str(e)}",
                        environment_id=environment_id,
                        exception=e,
                        correlation_id=correlation_id,
                    )
                    
        except Exception as e:
            logger.warning(
                f"Error getting additional status info: {str(e)}",
                environment_id=environment_id,
                exception=e,
                correlation_id=correlation_id,
            )
        
        return status_info
