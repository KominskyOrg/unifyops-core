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
        correlation_id=correlation_id,
    )

    # Construct the command
    cmd = ["terraform", operation.value]

    # Add operation-specific arguments
    if operation == TerraformOperation.INIT:
        cmd.extend(["-input=false", "-no-color", "-get=true"])
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
            with os.fdopen(fd, "w") as f:
                json.dump(variables, f)
            cmd.append(f"-var-file={var_file_path}")
        except Exception as e:
            logger.error(
                "Failed to create variable file",
                exception=e,
                execution_id=execution_id,
                correlation_id=correlation_id,
            )
            raise TerraformError(f"Failed to create variable file: {str(e)}")

    # Log the full command
    logger.debug(
        f"Executing Terraform command: {' '.join(cmd)}",
        command=" ".join(cmd),
        execution_id=execution_id,
        correlation_id=correlation_id,
    )

    try:
        # Run the command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=working_dir
        )

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

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
                        correlation_id=correlation_id,
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
                    correlation_id=correlation_id,
                )

                return TerraformResult(
                    operation=operation,
                    success=False,
                    output=stdout_text,
                    error=error_message,
                    duration_ms=duration_ms,
                    execution_id=execution_id,
                )

            # Log success
            logger.info(
                f"Terraform {operation.value} completed successfully",
                operation=operation.value,
                duration_ms=duration_ms,
                execution_id=execution_id,
                correlation_id=correlation_id,
            )

            # Return the result
            return TerraformResult(
                operation=operation,
                success=True,
                output=stdout_text,
                duration_ms=duration_ms,
                execution_id=execution_id,
                plan_id=execution_id if operation == TerraformOperation.PLAN else None,
                outputs=outputs,
            )

        except asyncio.TimeoutError:
            # If the process times out, kill it
            process.kill()
            logger.error(
                f"Terraform {operation.value} timed out after {timeout} seconds",
                operation=operation.value,
                timeout=timeout,
                execution_id=execution_id,
                correlation_id=correlation_id,
            )

            duration_ms = (time.time() - start_time) * 1000
            return TerraformResult(
                operation=operation,
                success=False,
                output="",
                error=f"Operation timed out after {timeout} seconds",
                duration_ms=duration_ms,
                execution_id=execution_id,
            )

    except Exception as e:
        # Catch any other exceptions
        logger.error(
            f"Error executing Terraform {operation.value}",
            exception=e,
            operation=operation.value,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )

        duration_ms = (time.time() - start_time) * 1000
        return TerraformResult(
            operation=operation,
            success=False,
            output="",
            error=str(e),
            duration_ms=duration_ms,
            execution_id=execution_id,
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
                    correlation_id=correlation_id,
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

    async def init(
        self,
        module_path: str,
        backend_config: Optional[Dict[str, str]] = None,
        force_module_download: bool = False,
        correlation_id: Optional[str] = None,
    ) -> TerraformResult:
        """
        Initialize a Terraform module

        Args:
            module_path: Path to the module relative to terraform_dir
            backend_config: Backend configuration
            force_module_download: Whether to force download modules from source
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
                with os.fdopen(fd, "w") as f:
                    for key, value in backend_config.items():
                        f.write(f'{key} = "{value}"\n')
                var_files.append(backend_file)
            except Exception as e:
                self.logger.error(
                    "Failed to create backend config file",
                    exception=e,
                    correlation_id=correlation_id,
                )
                raise TerraformError(f"Failed to create backend config file: {str(e)}")

        # First try cleaning the .terraform directory if force module download is enabled
        if force_module_download:
            terraform_dir = os.path.join(working_dir, ".terraform")
            if os.path.exists(terraform_dir):
                self.logger.info(
                    "Forcing module download: removing .terraform directory",
                    module_path=module_path,
                    correlation_id=correlation_id,
                )
                try:
                    import shutil

                    shutil.rmtree(terraform_dir)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to remove .terraform directory: {str(e)}",
                        exception=e,
                        correlation_id=correlation_id,
                    )

        try:
            # Run terraform init
            return await run_terraform_command(
                operation=TerraformOperation.INIT,
                working_dir=working_dir,
                var_files=var_files,
                correlation_id=correlation_id,
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
                        correlation_id=correlation_id,
                    )

    async def plan(
        self,
        module_path: str,
        variables: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> TerraformResult:
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
            correlation_id=correlation_id,
        )

    async def apply(
        self,
        module_path: str,
        variables: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
        plan_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> TerraformResult:
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
                correlation_id=correlation_id,
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode("utf-8") or stdout.decode("utf-8")
                self.logger.error(
                    "Failed to apply Terraform plan",
                    error=error_message,
                    plan_id=plan_id,
                    correlation_id=correlation_id,
                )

                raise TerraformError(f"Failed to apply plan: {error_message}")

            return TerraformResult(
                operation=TerraformOperation.APPLY,
                success=True,
                output=stdout.decode("utf-8"),
                duration_ms=0,  # We don't track duration for this case
                execution_id=str(uuid.uuid4()),
                plan_id=plan_id,
            )

        # Otherwise, run terraform apply directly
        return await run_terraform_command(
            operation=TerraformOperation.APPLY,
            working_dir=working_dir,
            variables=variables,
            auto_approve=auto_approve,
            correlation_id=correlation_id,
        )

    async def destroy(
        self,
        module_path: str,
        variables: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
        correlation_id: Optional[str] = None,
    ) -> TerraformResult:
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
            correlation_id=correlation_id,
        )

    async def output(
        self, module_path: str, correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
            correlation_id=correlation_id,
        )

        if not result.success:
            raise TerraformError(f"Failed to get outputs: {result.error}")

        return result.outputs

    def get_terraform_modules(self) -> List[Dict[str, Any]]:
        """
        Get a list of available Terraform modules with rich metadata

        Returns:
            List[Dict[str, Any]]: A list of modules with metadata including name, path, 
                                  description, category, provider, variables, and outputs
        """
        modules = []

        # Scan the terraform directory for modules
        for root, dirs, files in os.walk(self.terraform_dir):
            # Only consider directories that have a main.tf file
            if "main.tf" in files:
                relative_path = os.path.relpath(root, self.terraform_dir)
                name = os.path.basename(root)
                
                # Extract module metadata
                metadata = self._extract_module_metadata(root, name, relative_path)
                modules.append(metadata)

        return modules
        
    def _extract_module_metadata(self, module_dir: str, name: str, relative_path: str) -> Dict[str, Any]:
        """
        Extract detailed metadata from a Terraform module

        Args:
            module_dir: Absolute path to the module directory
            name: Module name
            relative_path: Path relative to terraform directory

        Returns:
            Dict[str, Any]: Module metadata
        """
        metadata = {
            "name": name,
            "path": relative_path,
            "description": "",
            "category": self._extract_category(relative_path),
            "provider": self._extract_provider(relative_path),
            "variables": [],
            "outputs": [],
            "dependencies": [],
            "tags": []
        }
        
        # Extract description from main.tf
        main_tf_path = os.path.join(module_dir, "main.tf")
        if os.path.exists(main_tf_path):
            with open(main_tf_path, "r") as f:
                content = f.read()
                # Try to find module description in comments at the top
                lines = content.split("\n")
                description_lines = []
                for line in lines:
                    line = line.strip()
                    if line.startswith("#") or line.startswith("//"):
                        description_lines.append(line.lstrip("#").lstrip("/").strip())
                    elif line and not line.isspace():
                        # Stop at first non-comment, non-empty line
                        break
                
                if description_lines:
                    metadata["description"] = " ".join(description_lines)
                else:
                    metadata["description"] = f"Terraform module: {name}"
        
        # Extract variables from variables.tf
        variables_path = os.path.join(module_dir, "variables.tf")
        if os.path.exists(variables_path):
            metadata["variables"] = self._extract_variables(variables_path)
            
        # Extract outputs from outputs.tf
        outputs_path = os.path.join(module_dir, "outputs.tf")
        if os.path.exists(outputs_path):
            metadata["outputs"] = self._extract_outputs(outputs_path)
            
        # Look for tags in README.md or module description
        readme_path = os.path.join(module_dir, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f:
                readme_content = f.read().lower()
                # Extract tags from README
                possible_tags = ["networking", "storage", "compute", "security", 
                                "database", "serverless", "kubernetes", "monitoring"]
                metadata["tags"] = [tag for tag in possible_tags if tag in readme_content]
        
        return metadata
    
    def _extract_category(self, path: str) -> str:
        """Extract category from module path"""
        parts = path.split(os.sep)
        if len(parts) >= 2:
            return parts[1]
        return "uncategorized"
    
    def _extract_provider(self, path: str) -> str:
        """Extract provider from module path"""
        parts = path.split(os.sep)
        if parts:
            return parts[0]
        return "unknown"
    
    def _extract_variables(self, variables_path: str) -> List[Dict[str, Any]]:
        """Extract variable definitions from variables.tf"""
        variables = []
        try:
            with open(variables_path, "r") as f:
                content = f.read()
                # Basic parsing - in a production system you might want to use a proper HCL parser
                import re
                var_blocks = re.findall(r'variable\s+"([^"]+)"\s+{([^}]+)}', content, re.DOTALL)
                
                for name, block in var_blocks:
                    variable = {"name": name}
                    
                    # Extract type
                    type_match = re.search(r'type\s+=\s+([^\n]+)', block)
                    if type_match:
                        variable["type"] = type_match.group(1).strip()
                    
                    # Extract description
                    desc_match = re.search(r'description\s+=\s+"([^"]+)"', block)
                    if desc_match:
                        variable["description"] = desc_match.group(1).strip()
                    
                    # Extract default value
                    default_match = re.search(r'default\s+=\s+([^\n]+)', block)
                    if default_match:
                        variable["default"] = default_match.group(1).strip()
                    
                    variables.append(variable)
        except Exception as e:
            self.logger.warning(f"Failed to extract variables from {variables_path}: {str(e)}")
        
        return variables
    
    def _extract_outputs(self, outputs_path: str) -> List[Dict[str, str]]:
        """Extract output definitions from outputs.tf"""
        outputs = []
        try:
            with open(outputs_path, "r") as f:
                content = f.read()
                # Basic parsing
                import re
                output_blocks = re.findall(r'output\s+"([^"]+)"\s+{([^}]+)}', content, re.DOTALL)
                
                for name, block in output_blocks:
                    output = {"name": name}
                    
                    # Extract description
                    desc_match = re.search(r'description\s+=\s+"([^"]+)"', block)
                    if desc_match:
                        output["description"] = desc_match.group(1).strip()
                    
                    outputs.append(output)
        except Exception as e:
            self.logger.warning(f"Failed to extract outputs from {outputs_path}: {str(e)}")
        
        return outputs


class EnvironmentGraph:
    """
    Service for managing module dependencies and creating environment configurations
    """
    
    def __init__(self, terraform_service: TerraformService):
        """
        Initialize the environment graph service
        
        Args:
            terraform_service: The Terraform service instance
        """
        self.terraform_service = terraform_service
        self.logger = get_logger("terraform.environment")
        
    def create_environment_config(
        self, 
        modules: List[str], 
        variables: Optional[Dict[str, Dict[str, Any]]] = None,
        environment_name: str = "custom-env",
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Create a Terraform configuration for a custom environment
        
        Args:
            modules: List of module paths to include
            variables: Variables for each module (keyed by module path)
            environment_name: Name for the environment
            correlation_id: Correlation ID for request tracing
            
        Returns:
            str: Path to the generated environment configuration
        """
        # Create a directory for the environment
        env_dir = os.path.join(self.terraform_service.terraform_dir, "environments", environment_name)
        os.makedirs(env_dir, exist_ok=True)
        
        # Create the main.tf file
        main_tf_content = self._generate_environment_config(modules, variables)
        with open(os.path.join(env_dir, "main.tf"), "w") as f:
            f.write(main_tf_content)
            
        # Create variables.tf
        variables_tf_content = self._generate_variables_file(modules)
        with open(os.path.join(env_dir, "variables.tf"), "w") as f:
            f.write(variables_tf_content)
            
        # Create outputs.tf
        outputs_tf_content = self._generate_outputs_file(modules)
        with open(os.path.join(env_dir, "outputs.tf"), "w") as f:
            f.write(outputs_tf_content)
            
        self.logger.info(
            f"Created environment configuration",
            environment=environment_name,
            modules=modules,
            correlation_id=correlation_id
        )
        
        return f"environments/{environment_name}"
    
    def _generate_environment_config(
        self, 
        modules: List[str],
        variables: Optional[Dict[str, Dict[str, Any]]]
    ) -> str:
        """Generate the main.tf file for the environment"""
        # Start with a comment header
        content = [
            "# Custom environment configuration",
            "# Generated automatically by UnifyOps Core",
            "# Do not edit this file directly - it will be overwritten",
            "",
            "terraform {",
            '  required_version = ">= 1.0.0"',
            "  backend \"s3\" {",
            "    # Backend configuration provided during terraform init",
            "  }",
            "}",
            ""
        ]
        
        # Include each module
        for i, module_path in enumerate(modules):
            module_name = os.path.basename(module_path)
            safe_name = f"{module_name}_{i}"
            
            module_block = [
                f'module "{safe_name}" {{',
                f'  source = "../{module_path}"',
                ""
            ]
            
            # Add variables if provided
            if variables and module_path in variables:
                for var_name, var_value in variables[module_path].items():
                    if isinstance(var_value, str):
                        module_block.append(f'  {var_name} = "{var_value}"')
                    else:
                        module_block.append(f'  {var_name} = {json.dumps(var_value)}')
            
            module_block.append("}")
            module_block.append("")
            
            content.extend(module_block)
            
        return "\n".join(content)
    
    def _generate_variables_file(self, modules: List[str]) -> str:
        """Generate the variables.tf file for the environment"""
        # Get complete module info to extract variables
        all_modules = self.terraform_service.get_terraform_modules()
        selected_modules = [m for m in all_modules if m["path"] in modules]
        
        content = [
            "# Variables for custom environment",
            "# Generated automatically by UnifyOps Core",
            ""
        ]
        
        # Create variable definitions for each module's variables
        for module in selected_modules:
            if module.get("variables"):
                for var in module["variables"]:
                    var_name = f"{module['name']}_{var['name']}"
                    content.append(f'variable "{var_name}" {{')
                    
                    if "type" in var:
                        content.append(f'  type = {var["type"]}')
                        
                    if "description" in var:
                        content.append(f'  description = "{var["description"]}"')
                        
                    if "default" in var:
                        if var.get("type", "").startswith("string"):
                            content.append(f'  default = "{var["default"]}"')
                        else:
                            content.append(f'  default = {var["default"]}')
                            
                    content.append("}")
                    content.append("")
                    
        return "\n".join(content)
    
    def _generate_outputs_file(self, modules: List[str]) -> str:
        """Generate the outputs.tf file for the environment"""
        # Get complete module info to extract outputs
        all_modules = self.terraform_service.get_terraform_modules()
        selected_modules = [m for m in all_modules if m["path"] in modules]
        
        content = [
            "# Outputs for custom environment",
            "# Generated automatically by UnifyOps Core",
            ""
        ]
        
        # Create outputs that reference each module's outputs
        for i, module in enumerate(selected_modules):
            module_name = module["name"]
            safe_name = f"{module_name}_{i}"
            
            if module.get("outputs"):
                for output in module["outputs"]:
                    output_name = f"{module_name}_{output['name']}"
                    
                    content.append(f'output "{output_name}" {{')
                    if "description" in output:
                        content.append(f'  description = "{output["description"]}"')
                    content.append(f'  value = module.{safe_name}.{output["name"]}')
                    content.append("}")
                    content.append("")
                    
        return "\n".join(content)
        
    def resolve_dependencies(
        self, 
        modules: List[str],
        correlation_id: Optional[str] = None
    ) -> List[List[str]]:
        """
        Resolve module dependencies and return modules in execution order
        
        Args:
            modules: List of module paths
            correlation_id: Correlation ID for request tracing
            
        Returns:
            List[List[str]]: Groups of modules that can be executed in parallel,
                           ordered by dependency level
        """
        # TODO: Implement dependency resolution based on module outputs and variables
        # For now, just return all modules as a single group
        return [modules]
