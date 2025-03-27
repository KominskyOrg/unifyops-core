from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import Dict, Any, List, Optional
import os
from enum import Enum

from app.core.config import get_settings, Settings
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.core.exceptions import TerraformError, BadRequestError, NotFoundError, ErrorResponse
from app.core.logging import get_logger
from app.schemas.terraform import (
    ErrorResponse, TerraformModule, TerraformInitRequest, TerraformPlanRequest,
    TerraformApplyRequest, TerraformDestroyRequest, TerraformInitResponse,
    TerraformPlanResponse, TerraformApplyResponse, TerraformDestroyResponse,
    ModulesResponse, OutputsResponse
)
    
# Create router with tags for documentation
router = APIRouter(
    prefix="/api/v1/terraform", 
    tags=["Terraform"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Resource Not Found", "model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Terraform Operation Error", "model": ErrorResponse},
    }
)
logger = get_logger("terraform.router")

# Get the base directory for Terraform modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TF_DIR = os.path.join(BASE_DIR, "app/tf")

# Create Terraform service
terraform_service = TerraformService(TF_DIR)


@router.get(
    "/modules", 
    response_model=ModulesResponse,
    status_code=status.HTTP_200_OK,
    summary="List available Terraform modules",
    description="Returns a list of all available Terraform modules in the system."
)
async def list_modules(
    request: Request,
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    List all available Terraform modules.
    
    Args:
        request: The HTTP request
        settings: Application settings
    
    Returns:
        A dictionary containing the list of modules and total count.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    
    logger.info(
        "Listing available Terraform modules",
        correlation_id=correlation_id
    )
    
    # Get modules from the service
    module_dicts = terraform_service.get_terraform_modules()
    
    # Convert to TerraformModule instances
    modules = [TerraformModule(**module_dict) for module_dict in module_dicts]
    
    return {
        "modules": [module.model_dump() for module in modules],
        "count": len(modules)
    }


@router.post(
    "/init", 
    response_model=TerraformInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize a Terraform module",
    description="""
    Initializes a Terraform module by running `terraform init`.
    This prepares the module for use by downloading providers and modules.
    """
)
async def init_module(
    request: Request,
    init_request: TerraformInitRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformInitResponse:
    """
    Initialize a Terraform module.
    
    Args:
        request: The HTTP request
        init_request: The initialization parameters
        settings: Application settings
        
    Returns:
        TerraformInitResponse: The result of the initialization operation
        
    Raises:
        NotFoundError: If the module is not found
        TerraformError: If the terraform init operation fails
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        f"Initializing Terraform module: {init_request.module_path}",
        module_path=init_request.module_path,
        correlation_id=correlation_id
    )
    
    try:
        # Check if the module exists
        module_path = os.path.join(TF_DIR, init_request.module_path)
        if not os.path.exists(module_path):
            raise NotFoundError(f"Module not found: {init_request.module_path}")
            
        # List available files in module directory to help with debugging
        files = os.listdir(module_path)
        logger.info(
            f"Module directory contents: {files}",
            module_path=init_request.module_path,
            files=files,
            correlation_id=correlation_id
        )
        
        # Check for terraform files
        if not any(f.endswith('.tf') for f in files):
            raise BadRequestError(f"No Terraform files found in module: {init_request.module_path}")
        
        # Run terraform init
        result = await terraform_service.init(
            module_path=init_request.module_path,
            backend_config=init_request.backend_config,
            force_module_download=init_request.force_module_download,
            correlation_id=correlation_id
        )
        
        # Better error handling for module-specific errors
        if not result.success and result.error and "subdir" in result.error and "not found" in result.error:
            logger.error(
                f"Module dependency error: {result.error}",
                module_path=init_request.module_path,
                error=result.error,
                correlation_id=correlation_id
            )
            
            # Extract the missing module path from the error message
            import re
            missing_module = re.search(r'subdir "([^"]+)" not found', result.error)
            if missing_module:
                missing_path = missing_module.group(1)
                error_msg = f"Missing module dependency: {missing_path}. Check module structure or use remote sources."
                logger.error(
                    error_msg,
                    module_path=init_request.module_path,
                    missing_module=missing_path,
                    correlation_id=correlation_id
                )
                raise TerraformError(error_msg)
        
        # Return the result
        return TerraformInitResponse(
            operation=result.operation.value,
            success=result.success,
            message="Terraform module initialized successfully" if result.success else result.error or "Initialization failed",
            execution_id=result.execution_id,
            duration_ms=result.duration_ms
        )
    except TerraformError as e:
        # Re-raise TerraformError
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(
            f"Error initializing Terraform module: {init_request.module_path}",
            exception=e,
            module_path=init_request.module_path,
            correlation_id=correlation_id
        )
        raise TerraformError(str(e))


@router.post(
    "/plan", 
    response_model=TerraformPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a Terraform plan",
    description="""
    Creates a Terraform execution plan that shows what actions Terraform 
    would take to apply the current configuration. This is a preview step before 
    actually making any changes to infrastructure.
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "Terraform plan result",
            "content": {
                "application/json": {
                    "example": {
                        "operation": "PLAN",
                        "success": True,
                        "message": "Terraform plan created successfully",
                        "execution_id": "plan-e5f6g7h8",
                        "duration_ms": 2367.81,
                        "plan_id": "plan-1234567890"
                    }
                }
            }
        }
    }
)
async def plan_module(
    request: Request,
    plan_request: TerraformPlanRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformPlanResponse:
    """
    Create a Terraform plan.
    
    Args:
        request: The HTTP request
        plan_request: The plan parameters
        settings: Application settings
        
    Returns:
        TerraformPlanResponse: The result of the plan operation
        
    Raises:
        NotFoundError: If the module is not found
        TerraformError: If the terraform plan operation fails
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        f"Planning Terraform module: {plan_request.module_path}",
        module_path=plan_request.module_path,
        correlation_id=correlation_id
    )
    
    try:
        # Check if the module exists
        module_path = os.path.join(TF_DIR, plan_request.module_path)
        if not os.path.exists(module_path):
            raise NotFoundError(f"Module not found: {plan_request.module_path}")
        
        # Run terraform plan
        result = await terraform_service.plan(
            module_path=plan_request.module_path,
            variables=plan_request.variables,
            correlation_id=correlation_id
        )
        
        # Return the result
        return TerraformPlanResponse(
            operation=result.operation.value,
            success=result.success,
            message="Terraform plan created successfully" if result.success else result.error or "Plan creation failed",
            execution_id=result.execution_id,
            duration_ms=result.duration_ms,
            plan_id=result.plan_id
        )
    except TerraformError as e:
        # Re-raise TerraformError
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(
            f"Error planning Terraform module: {plan_request.module_path}",
            exception=e,
            module_path=plan_request.module_path,
            correlation_id=correlation_id
        )
        raise TerraformError(str(e))


@router.post(
    "/apply", 
    response_model=TerraformApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply Terraform changes",
    description="""
    Applies the Terraform execution plan to create, update, or delete infrastructure 
    resources as needed to reach the desired state specified in the configuration.
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "Terraform apply result",
            "content": {
                "application/json": {
                    "example": {
                        "operation": "APPLY",
                        "success": True,
                        "message": "Terraform apply completed successfully",
                        "execution_id": "apply-i9j0k1l2",
                        "duration_ms": 5892.43,
                        "outputs": {
                            "bucket_arn": "arn:aws:s3:::my-application-bucket",
                            "bucket_domain_name": "my-application-bucket.s3.amazonaws.com",
                            "bucket_regional_domain_name": "my-application-bucket.s3.us-west-2.amazonaws.com"
                        }
                    }
                }
            }
        }
    }
)
async def apply_module(
    request: Request,
    apply_request: TerraformApplyRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformApplyResponse:
    """
    Apply Terraform changes.
    
    Args:
        request: The HTTP request
        apply_request: The apply parameters
        settings: Application settings
        
    Returns:
        TerraformApplyResponse: The result of the apply operation
        
    Raises:
        NotFoundError: If the module is not found
        TerraformError: If the terraform apply operation fails
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        f"Applying Terraform module: {apply_request.module_path}",
        module_path=apply_request.module_path,
        plan_id=apply_request.plan_id,
        correlation_id=correlation_id
    )
    
    try:
        # Check if the module exists
        module_path = os.path.join(TF_DIR, apply_request.module_path)
        if not os.path.exists(module_path):
            raise NotFoundError(f"Module not found: {apply_request.module_path}")
        
        # Run terraform apply
        result = await terraform_service.apply(
            module_path=apply_request.module_path,
            variables=apply_request.variables,
            auto_approve=apply_request.auto_approve,
            plan_id=apply_request.plan_id,
            correlation_id=correlation_id
        )
        
        # Get outputs if the apply was successful
        outputs = None
        if result.success:
            try:
                outputs = await terraform_service.output(
                    module_path=apply_request.module_path,
                    correlation_id=correlation_id
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get outputs after apply: {str(e)}",
                    module_path=apply_request.module_path,
                    correlation_id=correlation_id
                )
        
        # Return the result
        return TerraformApplyResponse(
            operation=result.operation.value,
            success=result.success,
            message="Terraform apply completed successfully" if result.success else result.error or "Apply failed",
            execution_id=result.execution_id,
            duration_ms=result.duration_ms,
            outputs=outputs
        )
    except TerraformError as e:
        # Re-raise TerraformError
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(
            f"Error applying Terraform module: {apply_request.module_path}",
            exception=e,
            module_path=apply_request.module_path,
            correlation_id=correlation_id
        )
        raise TerraformError(str(e))


@router.post(
    "/destroy", 
    response_model=TerraformDestroyResponse,
    status_code=status.HTTP_200_OK,
    summary="Destroy Terraform resources",
    description="""
    Destroys all the infrastructure resources managed by the Terraform module.
    This is a destructive operation and should be used with caution.
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "Terraform destroy result",
            "content": {
                "application/json": {
                    "example": {
                        "operation": "DESTROY",
                        "success": True,
                        "message": "Terraform destroy completed successfully",
                        "execution_id": "destroy-m3n4o5p6",
                        "duration_ms": 3421.67
                    }
                }
            }
        }
    }
)
async def destroy_module(
    request: Request,
    destroy_request: TerraformDestroyRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformDestroyResponse:
    """
    Destroy Terraform resources.
    
    Args:
        request: The HTTP request
        destroy_request: The destroy parameters
        settings: Application settings
        
    Returns:
        TerraformDestroyResponse: The result of the destroy operation
        
    Raises:
        NotFoundError: If the module is not found
        TerraformError: If the terraform destroy operation fails
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        f"Destroying Terraform module: {destroy_request.module_path}",
        module_path=destroy_request.module_path,
        correlation_id=correlation_id
    )
    
    try:
        # Check if the module exists
        module_path = os.path.join(TF_DIR, destroy_request.module_path)
        if not os.path.exists(module_path):
            raise NotFoundError(f"Module not found: {destroy_request.module_path}")
        
        # Run terraform destroy
        result = await terraform_service.destroy(
            module_path=destroy_request.module_path,
            variables=destroy_request.variables,
            auto_approve=destroy_request.auto_approve,
            correlation_id=correlation_id
        )
        
        # Return the result
        return TerraformDestroyResponse(
            operation=result.operation.value,
            success=result.success,
            message="Terraform destroy completed successfully" if result.success else result.error or "Destroy failed",
            execution_id=result.execution_id,
            duration_ms=result.duration_ms
        )
    except TerraformError as e:
        # Re-raise TerraformError
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(
            f"Error destroying Terraform module: {destroy_request.module_path}",
            exception=e,
            module_path=destroy_request.module_path,
            correlation_id=correlation_id
        )
        raise TerraformError(str(e))


@router.get(
    "/outputs/{module_path:path}", 
    response_model=OutputsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Terraform outputs",
    description="""
    Retrieves the output values from the state file for a given Terraform module.
    This provides the current output values, which represent exported attributes of resources.
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "Terraform outputs",
            "content": {
                "application/json": {
                    "example": {
                        "module": "aws/s3_bucket",
                        "outputs": {
                            "bucket_arn": "arn:aws:s3:::my-application-bucket",
                            "bucket_domain_name": "my-application-bucket.s3.amazonaws.com",
                            "bucket_regional_domain_name": "my-application-bucket.s3.us-west-2.amazonaws.com"
                        }
                    }
                }
            }
        }
    }
)
async def get_outputs(
    request: Request,
    module_path: str,
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get Terraform outputs for a module.
    
    Args:
        request: The HTTP request
        module_path: Path to the Terraform module relative to the tf directory
        settings: Application settings
        
    Returns:
        Dict: A dictionary containing the module path and outputs
        
    Raises:
        NotFoundError: If the module is not found
        TerraformError: If the terraform output operation fails
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        f"Getting Terraform outputs for module: {module_path}",
        module_path=module_path,
        correlation_id=correlation_id
    )
    
    try:
        # Check if the module exists
        full_module_path = os.path.join(TF_DIR, module_path)
        if not os.path.exists(full_module_path):
            raise NotFoundError(f"Module not found: {module_path}")
        
        # Get the outputs
        outputs = await terraform_service.output(
            module_path=module_path,
            correlation_id=correlation_id
        )
        
        # Return the outputs
        return {
            "module": module_path,
            "outputs": outputs
        }
    except TerraformError as e:
        # Re-raise TerraformError
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(
            f"Error getting Terraform outputs for module: {module_path}",
            exception=e,
            module_path=module_path,
            correlation_id=correlation_id
        )
        raise TerraformError(str(e)) 