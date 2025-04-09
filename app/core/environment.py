import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger, get_background_task_logger
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.models.environment import Environment, EnvironmentStatus
from app.models.resource import Resource
from app.core.exceptions import TerraformError, NotFoundError, BadRequestError

logger = get_logger("environment")


class EnvironmentService:
    """
    Service for managing Terraform environments, including their associated resources.
    This service orchestrates Terraform execution (init, plan, apply) for the entire environment.
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

    def _collect_resource_variables(self, db: Session, environment_id: str) -> Dict[str, Any]:
        """
        Collect variables from all resource definitions associated with an environment.

        Args:
            db: Database session
            environment_id: ID of the environment

        Returns:
            Dict[str, Any]: A dictionary structured for Terraform, 
                           e.g., {"resource_definitions": {"resource_name_1": {...vars...}, ...}}
        """
        environment = db.query(Environment).options(joinedload(Environment.resources)).filter(Environment.id == environment_id).first()
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")
            
        resource_definitions = {}
        for resource in environment.resources:
            if resource.variables: # Only include resources that have variables defined
                # Use resource name as the key, assuming names are unique within the environment
                resource_definitions[resource.name] = resource.variables
                
        # Combine environment-level variables with collected resource variables
        # The exact structure depends on how the Terraform module expects them.
        # Example: Nest resource definitions under a specific key.
        combined_vars = environment.variables.copy() if environment.variables else {}
        combined_vars["resource_definitions"] = resource_definitions
        
        logger.debug(
            f"Collected {len(resource_definitions)} resource definitions for environment {environment_id}", 
            environment_id=environment_id,
            resource_count=len(resource_definitions)
        )
        
        return combined_vars

    async def run_terraform_init(
        self,
        db: Session,
        environment_id: str,
        # variables arg is less relevant now, we collect them internally
        # variables: Optional[Dict[str, Any]] = None, 
    ) -> TerraformResult:
        """
        Run terraform init for an environment.
        Uses the environment's module_path and backend configuration.
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        correlation_id = environment.correlation_id or str(uuid.uuid4())
        self.update_environment_status(db, environment_id, EnvironmentStatus.INITIALIZING)
        task_logger = get_background_task_logger("environment", environment_id)

        try:
            backend_config = self._get_backend_config(environment_id)
            task_logger.info("Starting Terraform init", correlation_id=correlation_id, backend_config=backend_config)

            init_result = await self.terraform_service.init(
                module_path=environment.module_path,
                backend_config=backend_config,
                correlation_id=correlation_id,
            )

            self.update_environment_execution(
                db, environment_id, TerraformOperation.INIT, init_result.execution_id
            )

            if not init_result.success:
                error_message = init_result.error or "Initialization failed"
                task_logger.error(
                    f"Terraform init failed: {error_message}",
                    environment_id=environment_id,
                    error=error_message,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                task_logger.info("Terraform init successful", execution_id=init_result.execution_id, duration_ms=init_result.duration_ms)
                # Update status only if init ran successfully and it wasn't part of a larger provisioning task
                if environment.status == EnvironmentStatus.INITIALIZING:
                     self.update_environment_status(db, environment_id, EnvironmentStatus.PENDING)

            return init_result

        except Exception as e:
            error_message = str(e)
            task_logger.error(
                f"Error initializing environment: {error_message}",
                environment_id=environment_id,
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
        # variables are collected internally
        # variables: Optional[Dict[str, Any]] = None,
    ) -> TerraformResult:
        """
        Run Terraform plan for an environment, collecting all resource variables.
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment with ID {environment_id} not found")
            
        if environment.status in [EnvironmentStatus.APPLYING.value, EnvironmentStatus.DESTROYING.value]:
             raise BadRequestError(f"Environment is currently {environment.status}, cannot plan")

        correlation_id = environment.correlation_id or str(uuid.uuid4())
        self.update_environment_status(db, environment_id, EnvironmentStatus.PLANNING)
        task_logger = get_background_task_logger("environment", environment_id)

        try:
            # Ensure environment is initialized
            if not environment.init_execution_id:
                task_logger.info("Environment not initialized, running init first.", correlation_id=correlation_id)
                init_result = await self.run_terraform_init(db, environment_id)
                if not init_result.success:
                    # Status already set to FAILED by init
                    return init_result # Return init failure result
            
            # Collect variables from environment and all associated resources
            task_logger.info("Collecting resource variables for plan", correlation_id=correlation_id)
            all_variables = self._collect_resource_variables(db, environment_id)

            task_logger.info(
                f"Starting Terraform plan with {len(all_variables.get('resource_definitions', {}))} resource definitions", 
                correlation_id=correlation_id
            )
            plan_result = await self.terraform_service.plan(
                module_path=environment.module_path,
                variables=all_variables, # Pass combined variables
                correlation_id=correlation_id,
            )

            self.update_environment_execution(
                db, environment_id, TerraformOperation.PLAN, plan_result.execution_id
            )

            if not plan_result.success:
                error_message = plan_result.error or "Planning failed"
                task_logger.error(
                    f"Terraform plan failed: {error_message}",
                    environment_id=environment_id,
                    error=error_message,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                task_logger.info(
                    "Terraform plan successful", 
                    execution_id=plan_result.execution_id, 
                    duration_ms=plan_result.duration_ms,
                    plan_id=plan_result.plan_id
                )
                # Update status only if plan ran successfully and it wasn't part of provisioning
                if environment.status == EnvironmentStatus.PLANNING:
                     # Status becomes PENDING_APPLY or stays PLANNING based on auto_apply?
                     # For now, just PENDING, assuming apply is manual unless provisioning
                     self.update_environment_status(db, environment_id, EnvironmentStatus.PENDING) 

            return plan_result

        except Exception as e:
            error_message = str(e)
            task_logger.error(
                f"Error planning environment: {error_message}",
                environment_id=environment_id,
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
        # variables are collected internally
        # variables: Optional[Dict[str, Any]] = None,
    ) -> TerraformResult:
        """
        Run terraform apply for an environment using the collected resource variables.
        """
        environment = self.get_environment(db, environment_id)
        if not environment:
            raise NotFoundError(f"Environment not found: {environment_id}")

        correlation_id = environment.correlation_id or str(uuid.uuid4())
        self.update_environment_status(db, environment_id, EnvironmentStatus.APPLYING)
        task_logger = get_background_task_logger("environment", environment_id)

        try:
            # Ensure we have a valid plan ID from a previous plan run
            # Or, re-run plan if needed? For simplicity, assume plan must exist.
            if not environment.plan_execution_id:
                 task_logger.warning("No valid plan found. Running plan before apply.", correlation_id=correlation_id)
                 plan_result = await self.run_terraform_plan(db, environment_id)
                 if not plan_result.success:
                     # Status already set by plan
                     return plan_result # Return plan failure result
                 # Refresh environment to get the new plan_id
                 environment = self.get_environment(db, environment_id)
                 if not environment.plan_execution_id:
                     raise TerraformError("Failed to obtain a plan ID even after re-running plan.")

            # Collect variables again to ensure consistency, although plan should have used them.
            task_logger.info("Collecting resource variables for apply", correlation_id=correlation_id)
            all_variables = self._collect_resource_variables(db, environment_id)
            
            # Get backend config for state management
            backend_config = self._get_backend_config(environment_id)

            task_logger.info(
                f"Starting Terraform apply with {len(all_variables.get('resource_definitions', {}))} resource definitions", 
                correlation_id=correlation_id,
                plan_id=environment.plan_execution_id # Log the plan being applied
            )
            
            # Run terraform apply - assuming auto_approve=True for background tasks/API calls
            apply_result = await self.terraform_service.apply(
                module_path=environment.module_path,
                variables=all_variables, # Pass combined variables
                backend_config=backend_config, # Needed if apply does its own state locking/reading
                auto_approve=True, 
                plan_id=environment.plan_execution_id, # Optionally apply a specific plan file
                correlation_id=correlation_id,
            )

            self.update_environment_execution(
                db, environment_id, TerraformOperation.APPLY, apply_result.execution_id
            )

            if not apply_result.success:
                error_message = apply_result.error or "Apply failed"
                task_logger.error(
                    f"Terraform apply failed: {error_message}",
                    environment_id=environment_id,
                    error=error_message,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(
                    db, environment_id, EnvironmentStatus.FAILED, error_message
                )
            else:
                task_logger.info(
                    "Terraform apply successful", 
                    execution_id=apply_result.execution_id, 
                    duration_ms=apply_result.duration_ms
                )
                # Update status to PROVISIONED
                self.update_environment_status(db, environment_id, EnvironmentStatus.PROVISIONED)

            return apply_result

        except Exception as e:
            error_message = str(e)
            task_logger.error(
                f"Error applying environment: {error_message}",
                environment_id=environment_id,
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
        # variables are collected internally
        # variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Asynchronously provision an environment using the full Terraform workflow (init, plan, apply).
        Collects variables from all associated resource definitions.
        Designed to run as a background task.
        """
        task_logger = get_background_task_logger("environment", environment_id)
        environment = self.get_environment(db, environment_id)
        if not environment:
            task_logger.error(f"Environment not found: {environment_id}")
            return

        correlation_id = environment.correlation_id or str(uuid.uuid4())
        task_logger.info(
            f"Starting full provisioning of environment: {environment.name}",
            environment_id=environment_id,
            module_path=environment.module_path,
            auto_apply=environment.auto_apply,
            correlation_id=correlation_id,
        )

        try:
            # 1. Run terraform init
            init_result = await self.run_terraform_init(db, environment_id)
            if not init_result.success:
                # Status already set by init
                return

            # 2. Run terraform plan (uses collected variables)
            plan_result = await self.run_terraform_plan(db, environment_id)
            if not plan_result.success:
                # Status already set by plan
                return

            # 3. Check if we should apply (based on environment setting)
            if environment.auto_apply == "True":
                task_logger.info("Auto-apply enabled, proceeding with apply phase.", correlation_id=correlation_id)
                # Run terraform apply (uses collected variables)
                apply_result = await self.run_terraform_apply(db, environment_id)
                if not apply_result.success:
                    # Status already set by apply
                    return
                    
                # Apply successful, status is PROVISIONED (set by apply)
                task_logger.info(
                    f"Environment provisioned successfully: {environment.name}",
                    correlation_id=correlation_id,
                )
            else:
                # Auto-apply is false, stop after plan
                task_logger.info(
                    f"Environment planned successfully (auto_apply is false, apply skipped): {environment.name}",
                    correlation_id=correlation_id,
                )
                # Explicitly set status back to PENDING (or maybe a new PENDING_APPLY state?)
                self.update_environment_status(db, environment_id, EnvironmentStatus.PENDING)

        except Exception as e:
            error_message = str(e)
            task_logger.error(
                f"Error during environment provisioning workflow: {error_message}",
                environment_id=environment_id,
                exception=e,
                correlation_id=correlation_id,
            )
            # Ensure status is set to FAILED if an unexpected error occurs
            try:
                self.update_environment_status(db, environment_id, EnvironmentStatus.FAILED, error_message)
            except Exception as status_update_e:
                task_logger.error(f"Failed to update status to FAILED after provisioning error: {status_update_e}")

        finally:
            # Remove from running tasks list
            if environment_id in self.running_tasks:
                del self.running_tasks[environment_id]
            task_logger.info("Environment provisioning task finished.", correlation_id=correlation_id)

    def start_provisioning_task(self, db: Session, environment_id: str):
        """
        Start a background task to provision an environment.
        """
        # Check if task is already running
        if environment_id in self.running_tasks:
            logger.warning(f"Provisioning task already running for environment {environment_id}")
            # Maybe return current status or raise an error?
            return environment_id # For now, just return ID
            
        environment = self.get_environment(db, environment_id)
        if not environment:
             raise NotFoundError(f"Cannot start provisioning: Environment {environment_id} not found.")
             
        # Prevent starting new task if environment is in a non-terminal state
        if environment.status not in [EnvironmentStatus.PENDING.value, EnvironmentStatus.FAILED.value, EnvironmentStatus.PROVISIONED.value]:
            raise BadRequestError(f"Cannot start provisioning: Environment is currently in status '{environment.status}'")
            
        # Update status to indicate provisioning is starting (e.g., QUEUED or PENDING)
        # Using PENDING for now as the task starts immediately
        self.update_environment_status(db, environment_id, EnvironmentStatus.PENDING) 
        
        # Create and store the background task
        task = asyncio.create_task(self.provision_environment(db, environment_id))
        self.running_tasks[environment_id] = task
        logger.info(f"Started background provisioning task for environment {environment_id}")
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

    async def delete_environment(
        self,
        db: Session,
        environment_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Delete an environment and its associated infrastructure
        
        Args:
            db: Database session
            environment_id: Environment ID
            correlation_id: Correlation ID for request tracing
        """
        # Set up logging for this background task
        task_logger = get_background_task_logger("environment", environment_id)
        
        # Get the environment
        environment = self.get_environment(db, environment_id)
        if not environment:
            task_logger.error(
                f"Environment not found: {environment_id}",
                environment_id=environment_id,
                correlation_id=correlation_id,
            )
            return
        
        task_logger.info(
            f"Starting destruction of environment: {environment.name}",
            environment_id=environment_id,
            module_path=environment.module_path,
            correlation_id=correlation_id,
        )
        
        # Update environment status to indicate deletion in progress
        self.update_environment_status(db, environment_id, EnvironmentStatus.DESTROYING)
        
        try:
            # 1. Make sure the directory exists
            module_path = os.path.join(self.terraform_service.base_dir, environment.module_path)
            if not os.path.exists(module_path):
                raise NotFoundError(f"Module path not found: {environment.module_path}")
            
            # 2. Run terraform init to ensure backend is configured
            init_result = await self.terraform_service.init(
                module_path=environment.module_path,
                backend_config=self._get_backend_config(environment_id),
                correlation_id=correlation_id,
            )
            
            if not init_result.success:
                error_message = init_result.error or "Unknown init error"
                task_logger.error(
                    f"Failed to initialize Terraform for environment deletion: {error_message}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(db, environment_id, EnvironmentStatus.FAILED, error_message)
                return
            
            # 3. Collect variables for this environment
            variables = self._collect_resource_variables(db, environment_id)
            
            # 4. Run terraform destroy
            destroy_result = await self.terraform_service.destroy(
                module_path=environment.module_path,
                variables=variables,
                auto_approve=True,  # Auto-approve the destroy
                correlation_id=correlation_id,
            )
            
            if not destroy_result.success:
                error_message = destroy_result.error or "Unknown destroy error"
                task_logger.error(
                    f"Failed to destroy environment infrastructure: {error_message}",
                    environment_id=environment_id,
                    module_path=environment.module_path,
                    correlation_id=correlation_id,
                )
                self.update_environment_status(db, environment_id, EnvironmentStatus.FAILED, error_message)
                return
            
            # 5. Delete the environment record from the database
            task_logger.info(
                f"Successfully destroyed environment infrastructure, deleting database record",
                environment_id=environment_id,
                module_path=environment.module_path,
                correlation_id=correlation_id,
            )
            
            # Delete environment from database
            db.delete(environment)
            db.commit()
            
            task_logger.info(
                f"Successfully deleted environment: {environment.name}",
                environment_id=environment_id,
                correlation_id=correlation_id,
            )
            
        except Exception as e:
            error_message = str(e)
            task_logger.error(
                f"Error during environment deletion: {error_message}",
                environment_id=environment_id,
                exception=e,
                correlation_id=correlation_id,
            )
            # Update status to FAILED if an unexpected error occurs
            try:
                self.update_environment_status(db, environment_id, EnvironmentStatus.FAILED, error_message)
            except Exception as status_update_e:
                task_logger.error(
                    f"Failed to update status to FAILED after delete error: {status_update_e}",
                    environment_id=environment_id,
                    correlation_id=correlation_id,
                )
