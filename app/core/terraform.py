import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel

from app.core.exceptions import TerraformError
from app.core.logging import get_logger

logger = get_logger("terraform")


class TerraformOperation(str, Enum):
    """Supported Terraform operations"""
    INIT = "init"
    PLAN = "plan"
    APPLY = "apply"
    DESTROY = "destroy"
    VALIDATE = "validate"
    OUTPUT = "output"


class TerraformResult(BaseModel):
    """Model for Terraform operation results"""
    operation: TerraformOperation
    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float
    execution_id: str
    plan_id: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None


async def run_terraform_command(
    operation: TerraformOperation,
    working_dir: str,
    variables: Optional[Dict[str, Any]] = None,
    var_files: Optional[List[str]] = None,
    auto_approve: bool = False,
    timeout: int = 600,
    execution_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> TerraformResult:
    """
    Run a Terraform command asynchronously
    
    Args:
        operation: The Terraform operation to perform
        working_dir: Directory containing Terraform files
        variables: Variables to pass to Terraform
        var_files: Variable files to pass to Terraform
        auto_approve: Whether to auto-approve the operation
        timeout: Timeout in seconds
        execution_id: Unique identifier for this execution
        correlation_id: Correlation ID for request tracing
        
    Returns:
        TerraformResult: The result of the operation
    """
    import time
    start_time = time.time()
    
    # Generate execution ID if not provided
    execution_id = execution_id or str(uuid.uuid4())
    
    # Log the operation start
    logger.info(
        f"Starting Terraform {operation.value}",
        operation=operation.value,
        working_dir=working_dir,
        execution_id=execution_id,
        correlation_id=correlation_id
    )
    
    # Construct the command
    cmd = ["terraform", operation.value]
    
    # Add operation-specific arguments
    if operation == TerraformOperation.INIT:
        cmd.extend(["-input=false", "-no-color"])
    elif operation in [TerraformOperation.APPLY, TerraformOperation.DESTROY]:
        if auto_approve:
            cmd.append("-auto-approve")
        cmd.extend(["-input=false", "-no-color"])
    elif operation == TerraformOperation.PLAN:
        plan_file = f"tfplan_{execution_id}"
        cmd.extend(["-input=false", "-no-color", f"-out={plan_file}"])
    elif operation == TerraformOperation.OUTPUT:
        cmd.append("-json")
    
    # Add variable files if provided
    if var_files:
        for var_file in var_files:
            cmd.append(f"-var-file={var_file}")
    
    # Create a temporary file for variables if provided
    var_file_path = None
    if variables:
        try:
            # Create temporary file for variables
            fd, var_file_path = tempfile.mkstemp(suffix=".tfvars.json")
            with os.fdopen(fd, 'w') as f:
                json.dump(variables, f)
            cmd.append(f"-var-file={var_file_path}")
        except Exception as e:
            logger.error(
                "Failed to create variable file",
                exception=e,
                execution_id=execution_id,
                correlation_id=correlation_id
            )
            raise TerraformError(f"Failed to create variable file: {str(e)}")
    
    # Log the full command
    logger.debug(
        f"Executing Terraform command: {' '.join(cmd)}",
        command=' '.join(cmd),
        execution_id=execution_id,
        correlation_id=correlation_id
    )
    
    try:
        # Run the command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )
        
        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            stdout_text = stdout.decode('utf-8')
            stderr_text = stderr.decode('utf-8')
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Parse outputs for output operation
            outputs = None
            if operation == TerraformOperation.OUTPUT and process.returncode == 0:
                try:
                    outputs = json.loads(stdout_text)
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse Terraform outputs as JSON",
                        execution_id=execution_id,
                        correlation_id=correlation_id
                    )
            
            # Check if operation was successful
            if process.returncode != 0:
                error_message = stderr_text or stdout_text
                logger.error(
                    f"Terraform {operation.value} failed",
                    operation=operation.value,
                    error=error_message,
                    exit_code=process.returncode,
                    duration_ms=duration_ms,
                    execution_id=execution_id,
                    correlation_id=correlation_id
                )
                
                return TerraformResult(
                    operation=operation,
                    success=False,
                    output=stdout_text,
                    error=error_message,
                    duration_ms=duration_ms,
                    execution_id=execution_id
                )
            
            # Log success
            logger.info(
                f"Terraform {operation.value} completed successfully",
                operation=operation.value,
                duration_ms=duration_ms,
                execution_id=execution_id,
                correlation_id=correlation_id
            )
            
            # Return the result
            return TerraformResult(
                operation=operation,
                success=True,
                output=stdout_text,
                duration_ms=duration_ms,
                execution_id=execution_id,
                plan_id=execution_id if operation == TerraformOperation.PLAN else None,
                outputs=outputs
            )
            
        except asyncio.TimeoutError:
            # If the process times out, kill it
            process.kill()
            logger.error(
                f"Terraform {operation.value} timed out after {timeout} seconds",
                operation=operation.value,
                timeout=timeout,
                execution_id=execution_id,
                correlation_id=correlation_id
            )
            
            duration_ms = (time.time() - start_time) * 1000
            return TerraformResult(
                operation=operation,
                success=False,
                output="",
                error=f"Operation timed out after {timeout} seconds",
                duration_ms=duration_ms,
                execution_id=execution_id
            )
    
    except Exception as e:
        # Catch any other exceptions
        logger.error(
            f"Error executing Terraform {operation.value}",
            exception=e,
            operation=operation.value,
            execution_id=execution_id,
            correlation_id=correlation_id
        )
        
        duration_ms = (time.time() - start_time) * 1000
        return TerraformResult(
            operation=operation,
            success=False,
            output="",
            error=str(e),
            duration_ms=duration_ms,
            execution_id=execution_id
        )
    
    finally:
        # Clean up the temporary variable file
        if var_file_path and os.path.exists(var_file_path):
            try:
                os.remove(var_file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to remove temporary var file: {var_file_path}",
                    exception=e,
                    execution_id=execution_id,
                    correlation_id=correlation_id
                )


class TerraformService:
    """Service for managing Terraform operations"""
    
    def __init__(self, terraform_dir: str):
        """
        Initialize the Terraform service
        
        Args:
            terraform_dir: Base directory containing Terraform modules
        """
        self.terraform_dir = terraform_dir
        self.logger = get_logger("terraform.service")
    
    async def init(self, module_path: str, backend_config: Optional[Dict[str, str]] = None, 
                  correlation_id: Optional[str] = None) -> TerraformResult:
        """
        Initialize a Terraform module
        
        Args:
            module_path: Path to the module relative to terraform_dir
            backend_config: Backend configuration
            correlation_id: Correlation ID for request tracing
        
        Returns:
            TerraformResult: The result of the operation
        """
        working_dir = os.path.join(self.terraform_dir, module_path)
        
        # Create a temporary backend config file if provided
        var_files = []
        if backend_config:
            fd, backend_file = tempfile.mkstemp(suffix=".tfbackend")
            try:
                with os.fdopen(fd, 'w') as f:
                    for key, value in backend_config.items():
                        f.write(f"{key} = \"{value}\"\n")
                var_files.append(backend_file)
            except Exception as e:
                self.logger.error(
                    "Failed to create backend config file",
                    exception=e,
                    correlation_id=correlation_id
                )
                raise TerraformError(f"Failed to create backend config file: {str(e)}")
        
        try:
            # Run terraform init
            return await run_terraform_command(
                operation=TerraformOperation.INIT,
                working_dir=working_dir,
                var_files=var_files,
                correlation_id=correlation_id
            )
        finally:
            # Clean up the temporary backend file
            if backend_config and os.path.exists(backend_file):
                try:
                    os.remove(backend_file)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to remove temporary backend file: {backend_file}",
                        exception=e,
                        correlation_id=correlation_id
                    )
    
    async def plan(self, module_path: str, variables: Optional[Dict[str, Any]] = None,
                  correlation_id: Optional[str] = None) -> TerraformResult:
        """
        Create a Terraform plan
        
        Args:
            module_path: Path to the module relative to terraform_dir
            variables: Variables to pass to Terraform
            correlation_id: Correlation ID for request tracing
            
        Returns:
            TerraformResult: The result of the operation
        """
        working_dir = os.path.join(self.terraform_dir, module_path)
        
        # Run terraform plan
        return await run_terraform_command(
            operation=TerraformOperation.PLAN,
            working_dir=working_dir,
            variables=variables,
            correlation_id=correlation_id
        )
    
    async def apply(self, module_path: str, variables: Optional[Dict[str, Any]] = None,
                   auto_approve: bool = False, plan_id: Optional[str] = None,
                   correlation_id: Optional[str] = None) -> TerraformResult:
        """
        Apply Terraform changes
        
        Args:
            module_path: Path to the module relative to terraform_dir
            variables: Variables to pass to Terraform
            auto_approve: Whether to auto-approve the operation
            plan_id: ID of a previously created plan to apply
            correlation_id: Correlation ID for request tracing
            
        Returns:
            TerraformResult: The result of the operation
        """
        working_dir = os.path.join(self.terraform_dir, module_path)
        
        # If plan_id is provided, apply that plan
        if plan_id:
            cmd = ["terraform", "apply", f"tfplan_{plan_id}"]
            
            self.logger.info(
                f"Applying Terraform plan {plan_id}",
                plan_id=plan_id,
                working_dir=working_dir,
                correlation_id=correlation_id
            )
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode('utf-8') or stdout.decode('utf-8')
                self.logger.error(
                    "Failed to apply Terraform plan",
                    error=error_message,
                    plan_id=plan_id,
                    correlation_id=correlation_id
                )
                
                raise TerraformError(f"Failed to apply plan: {error_message}")
            
            return TerraformResult(
                operation=TerraformOperation.APPLY,
                success=True,
                output=stdout.decode('utf-8'),
                duration_ms=0,  # We don't track duration for this case
                execution_id=str(uuid.uuid4()),
                plan_id=plan_id
            )
        
        # Otherwise, run terraform apply directly
        return await run_terraform_command(
            operation=TerraformOperation.APPLY,
            working_dir=working_dir,
            variables=variables,
            auto_approve=auto_approve,
            correlation_id=correlation_id
        )
    
    async def destroy(self, module_path: str, variables: Optional[Dict[str, Any]] = None,
                     auto_approve: bool = False, correlation_id: Optional[str] = None) -> TerraformResult:
        """
        Destroy Terraform resources
        
        Args:
            module_path: Path to the module relative to terraform_dir
            variables: Variables to pass to Terraform
            auto_approve: Whether to auto-approve the operation
            correlation_id: Correlation ID for request tracing
            
        Returns:
            TerraformResult: The result of the operation
        """
        working_dir = os.path.join(self.terraform_dir, module_path)
        
        # Run terraform destroy
        return await run_terraform_command(
            operation=TerraformOperation.DESTROY,
            working_dir=working_dir,
            variables=variables,
            auto_approve=auto_approve,
            correlation_id=correlation_id
        )
    
    async def output(self, module_path: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Terraform outputs
        
        Args:
            module_path: Path to the module relative to terraform_dir
            correlation_id: Correlation ID for request tracing
            
        Returns:
            Dict[str, Any]: The outputs
        """
        working_dir = os.path.join(self.terraform_dir, module_path)
        
        # Run terraform output
        result = await run_terraform_command(
            operation=TerraformOperation.OUTPUT,
            working_dir=working_dir,
            correlation_id=correlation_id
        )
        
        if not result.success:
            raise TerraformError(f"Failed to get outputs: {result.error}")
        
        return result.outputs 