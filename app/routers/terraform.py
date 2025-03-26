from fastapi import APIRouter, Depends, Request, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os

from app.core.config import get_settings, Settings
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.core.exceptions import TerraformError, BadRequestError, NotFoundError
from app.core.logging import get_logger

# Create router with tags for documentation
router = APIRouter(prefix="/terraform", tags=["Terraform"])
logger = get_logger("terraform.router")

# Get the base directory for Terraform modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TF_DIR = os.path.join(BASE_DIR, "tf")

# Create Terraform service
terraform_service = TerraformService(TF_DIR)


class TerraformModule(BaseModel):
    """Model for Terraform module information"""
    name: str
    path: str
    description: str


class TerraformRequest(BaseModel):
    """Base model for Terraform operation requests"""
    module_path: str
    variables: Optional[Dict[str, Any]] = None


class TerraformInitRequest(TerraformRequest):
    """Model for Terraform init requests"""
    backend_config: Optional[Dict[str, str]] = None


class TerraformPlanRequest(TerraformRequest):
    """Model for Terraform plan requests"""
    pass


class TerraformApplyRequest(TerraformRequest):
    """Model for Terraform apply requests"""
    auto_approve: bool = False
    plan_id: Optional[str] = None


class TerraformDestroyRequest(TerraformRequest):
    """Model for Terraform destroy requests"""
    auto_approve: bool = False


class TerraformResponse(BaseModel):
    """Base model for Terraform operation responses"""
    operation: str
    success: bool
    message: str
    execution_id: str
    duration_ms: float
    plan_id: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None


def get_terraform_modules() -> List[TerraformModule]:
    """Get a list of available Terraform modules"""
    modules = []
    
    # Scan the tf directory for modules
    for root, dirs, files in os.walk(TF_DIR):
        # Only consider directories that have a main.tf file
        if "main.tf" in files:
            relative_path = os.path.relpath(root, TF_DIR)
            name = os.path.basename(root)
            
            # Read the first line of main.tf to get the description
            with open(os.path.join(root, "main.tf"), "r") as f:
                first_line = f.readline().strip()
                description = first_line.lstrip("# ")
                if description == first_line:  # No comment found
                    description = f"Terraform module: {name}"
            
            modules.append(TerraformModule(
                name=name,
                path=relative_path,
                description=description
            ))
    
    return modules


@router.get("/modules", status_code=status.HTTP_200_OK)
async def list_modules(
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    List available Terraform modules
    """
    modules = get_terraform_modules()
    return {
        "modules": [module.model_dump() for module in modules],
        "count": len(modules)
    }


@router.post("/init", status_code=status.HTTP_200_OK)
async def init_module(
    request: Request,
    init_request: TerraformInitRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformResponse:
    """
    Initialize a Terraform module
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
        
        # Run terraform init
        result = await terraform_service.init(
            module_path=init_request.module_path,
            backend_config=init_request.backend_config,
            correlation_id=correlation_id
        )
        
        # Return the result
        return TerraformResponse(
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


@router.post("/plan", status_code=status.HTTP_200_OK)
async def plan_module(
    request: Request,
    plan_request: TerraformPlanRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformResponse:
    """
    Create a Terraform plan
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
        return TerraformResponse(
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


@router.post("/apply", status_code=status.HTTP_200_OK)
async def apply_module(
    request: Request,
    apply_request: TerraformApplyRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformResponse:
    """
    Apply Terraform changes
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
        return TerraformResponse(
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


@router.post("/destroy", status_code=status.HTTP_200_OK)
async def destroy_module(
    request: Request,
    destroy_request: TerraformDestroyRequest,
    settings: Settings = Depends(get_settings)
) -> TerraformResponse:
    """
    Destroy Terraform resources
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
        return TerraformResponse(
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


@router.get("/outputs/{module_path:path}", status_code=status.HTTP_200_OK)
async def get_outputs(
    request: Request,
    module_path: str,
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get Terraform outputs for a module
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