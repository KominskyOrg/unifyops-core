from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.models.terraform import Environment, Resource, Connection, Deployment
from app.schemas import (
    EnvironmentCreate, 
    EnvironmentUpdate,
    EnvironmentResponse,
    EnvironmentDetailResponse,
    ResourceCreate,
    ResourceResponse,
    ConnectionCreate,
    ConnectionResponse,
    EnvironmentResourcesRequest,
    DesignerStateRequest,
    DesignerStateResponse,
    EnvironmentDeployRequest
)
from app.core.terraform import TerraformService, EnvironmentGraph, TerraformOperation
from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(
    prefix="/environments",
    tags=["environments"],
    responses={404: {"description": "Not found"}},
)

logger = get_logger("api.environments")

# Create Terraform services
terraform_service = TerraformService(settings.TERRAFORM_DIR)
environment_graph = EnvironmentGraph(terraform_service)


@router.post("/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    request: EnvironmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new environment
    """
    # Create new environment
    db_environment = Environment(
        name=request.name,
        description=request.description,
        organization_id=str(request.organization_id),
        team_id=str(request.team_id) if request.team_id else None,
        created_by=request.created_by,
        variables=request.variables,
        tags=request.tags
    )
    
    db.add(db_environment)
    db.commit()
    db.refresh(db_environment)
    
    return db_environment


@router.get("/", response_model=List[EnvironmentResponse])
async def list_environments(
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    db: Session = Depends(get_db)
):
    """
    List environments with optional filtering
    """
    query = db.query(Environment)
    
    if organization_id:
        query = query.filter(Environment.organization_id == str(organization_id))
    
    if team_id:
        query = query.filter(Environment.team_id == str(team_id))
    
    environments = query.offset(skip).limit(limit).all()
    return environments


@router.get("/{environment_id}", response_model=EnvironmentDetailResponse)
async def get_environment(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about an environment
    """
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    return environment


@router.put("/{environment_id}", response_model=EnvironmentResponse)
async def update_environment(
    environment_id: UUID,
    request: EnvironmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an environment
    """
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    # Update fields if provided
    if request.name is not None:
        environment.name = request.name
    
    if request.description is not None:
        environment.description = request.description
    
    if request.team_id is not None:
        environment.team_id = str(request.team_id)
    
    if request.variables is not None:
        environment.variables = request.variables
    
    if request.tags is not None:
        environment.tags = request.tags
    
    db.commit()
    db.refresh(environment)
    
    return environment


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete an environment (does not destroy infrastructure)
    """
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    db.delete(environment)
    db.commit()
    
    return None


@router.post("/{environment_id}/resources", response_model=ResourceResponse)
async def add_resource(
    environment_id: UUID,
    request: ResourceCreate,
    db: Session = Depends(get_db)
):
    """
    Add a resource to an environment
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    # Create new resource
    db_resource = Resource(
        name=request.name,
        module_path=request.module_path,
        resource_type=request.resource_type,
        provider=request.provider,
        environment_id=str(environment_id),
        variables=request.variables,
        position_x=request.position_x,
        position_y=request.position_y
    )
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    return db_resource


@router.post("/{environment_id}/connections", response_model=ConnectionResponse)
async def add_connection(
    environment_id: UUID,
    request: ConnectionCreate,
    db: Session = Depends(get_db)
):
    """
    Add a connection between resources in an environment
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    # Check if resources exist and belong to this environment
    source = db.query(Resource).filter(
        Resource.id == str(request.source_id),
        Resource.environment_id == str(environment_id)
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source resource {request.source_id} not found in environment {environment_id}"
        )
    
    target = db.query(Resource).filter(
        Resource.id == str(request.target_id),
        Resource.environment_id == str(environment_id)
    ).first()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target resource {request.target_id} not found in environment {environment_id}"
        )
    
    # Create new connection
    db_connection = Connection(
        source_id=str(request.source_id),
        target_id=str(request.target_id),
        connection_type=request.connection_type,
        name=request.name,
        description=request.description,
        configuration=request.configuration
    )
    
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    
    return db_connection


@router.post("/{environment_id}/designer-state", response_model=DesignerStateResponse)
async def save_designer_state(
    environment_id: UUID,
    request: DesignerStateRequest,
    db: Session = Depends(get_db)
):
    """
    Save the complete designer state (resources and connections) for an environment
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    # Delete existing resources and connections
    db.query(Connection).filter(
        Connection.source_id.in_([r.id for r in environment.resources])
    ).delete(synchronize_session=False)
    
    db.query(Resource).filter(Resource.environment_id == str(environment_id)).delete(synchronize_session=False)
    
    # Create new resources
    db_resources = []
    for resource in request.resources:
        db_resource = Resource(
            name=resource.name,
            module_path=resource.module_path,
            resource_type=resource.resource_type,
            provider=resource.provider,
            environment_id=str(environment_id),
            variables=resource.variables,
            position_x=resource.position_x,
            position_y=resource.position_y
        )
        db_resources.append(db_resource)
        db.add(db_resource)
    
    db.commit()
    
    # Create resource id mapping (temporary id -> database id)
    resource_id_map = {str(req_res.id): db_res.id for req_res, db_res in zip(request.resources, db_resources)}
    
    # Create new connections
    db_connections = []
    for connection in request.connections:
        # Map the source and target ids to the newly created resources
        source_id = resource_id_map.get(str(connection.source_id))
        target_id = resource_id_map.get(str(connection.target_id))
        
        if not source_id or not target_id:
            # Skip invalid connections
            continue
        
        db_connection = Connection(
            source_id=source_id,
            target_id=target_id,
            connection_type=connection.connection_type,
            name=connection.name,
            description=connection.description,
            configuration=connection.configuration
        )
        db_connections.append(db_connection)
        db.add(db_connection)
    
    db.commit()
    
    # Refresh environment to get updated resources and connections
    db.refresh(environment)
    
    return DesignerStateResponse(
        environment_id=environment_id,
        resources=db_resources,
        connections=db_connections
    )


@router.post("/{environment_id}/generate-terraform", response_model=EnvironmentResponse)
async def generate_terraform(
    environment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate Terraform configuration for an environment based on its resources and connections
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    # Get resources for the environment
    resources = db.query(Resource).filter(Resource.environment_id == str(environment_id)).all()
    
    if not resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment {environment_id} has no resources"
        )
    
    # Get module paths from resources
    module_paths = [resource.module_path for resource in resources]
    
    # Prepare variables for modules
    variables = {}
    for resource in resources:
        if resource.variables:
            variables[resource.module_path] = resource.variables
    
    try:
        # Generate Terraform configuration
        tf_path = environment_graph.create_environment_config(
            modules=module_paths,
            variables=variables,
            environment_name=f"env-{environment_id}"
        )
        
        # Update environment with Terraform directory
        environment.terraform_dir = tf_path
        db.commit()
        
        return environment
        
    except Exception as e:
        logger.error(f"Failed to generate Terraform config: {str(e)}", environment_id=str(environment_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Terraform configuration: {str(e)}"
        )


@router.post("/{environment_id}/deploy", response_model=EnvironmentResponse)
async def deploy_environment(
    environment_id: UUID,
    request: EnvironmentDeployRequest,
    db: Session = Depends(get_db)
):
    """
    Deploy an environment using Terraform
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    if not environment.terraform_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment {environment_id} has no Terraform configuration. Generate it first."
        )
    
    try:
        # First initialize Terraform
        init_result = await terraform_service.init(environment.terraform_dir)
        if not init_result.success:
            # Create deployment record for failed initialization
            db_deployment = Deployment(
                environment_id=str(environment_id),
                execution_id=init_result.execution_id,
                operation=TerraformOperation.INIT.value,
                status="FAILED",
                initiated_by="system",  # Should be the user ID in production
                output=init_result.output,
                error=init_result.error
            )
            db.add(db_deployment)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Terraform: {init_result.error}"
            )
        
        # Then apply the configuration
        apply_result = await terraform_service.apply(
            module_path=environment.terraform_dir,
            variables=request.variables,
            auto_approve=request.auto_approve
        )
        
        # Create deployment record
        db_deployment = Deployment(
            environment_id=str(environment_id),
            execution_id=apply_result.execution_id,
            operation=TerraformOperation.APPLY.value,
            status="SUCCEEDED" if apply_result.success else "FAILED",
            initiated_by="system",  # Should be the user ID in production
            output=apply_result.output,
            error=apply_result.error
        )
        db.add(db_deployment)
        
        # Update environment status
        if apply_result.success:
            environment.status = "DEPLOYED"
            environment.last_deployed_at = db_deployment.started_at
            
            # Update resource outputs if available
            if apply_result.outputs:
                # Process outputs to map them to resources
                for resource in environment.resources:
                    resource_name = resource.name.lower().replace(" ", "_")
                    resource_outputs = {}
                    
                    # Find outputs for this resource
                    for output_key, output_value in apply_result.outputs.items():
                        if output_key.startswith(f"{resource_name}_"):
                            output_name = output_key[len(f"{resource_name}_"):]
                            resource_outputs[output_name] = output_value["value"]
                    
                    if resource_outputs:
                        resource.outputs = resource_outputs
        else:
            environment.status = "FAILED"
        
        db.commit()
        
        # If apply failed, raise exception
        if not apply_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deploy environment: {apply_result.error}"
            )
        
        return environment
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to deploy environment: {str(e)}", environment_id=str(environment_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy environment: {str(e)}"
        )


@router.post("/{environment_id}/destroy", response_model=EnvironmentResponse)
async def destroy_environment(
    environment_id: UUID,
    auto_approve: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Destroy the infrastructure for an environment
    """
    # Check if environment exists
    environment = db.query(Environment).filter(Environment.id == str(environment_id)).first()
    
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    if not environment.terraform_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment {environment_id} has no Terraform configuration"
        )
    
    try:
        # First initialize Terraform
        init_result = await terraform_service.init(environment.terraform_dir)
        if not init_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Terraform: {init_result.error}"
            )
        
        # Then destroy the resources
        destroy_result = await terraform_service.destroy(
            module_path=environment.terraform_dir,
            auto_approve=auto_approve
        )
        
        # Create deployment record
        db_deployment = Deployment(
            environment_id=str(environment_id),
            execution_id=destroy_result.execution_id,
            operation=TerraformOperation.DESTROY.value,
            status="SUCCEEDED" if destroy_result.success else "FAILED",
            initiated_by="system",  # Should be the user ID in production
            output=destroy_result.output,
            error=destroy_result.error
        )
        db.add(db_deployment)
        
        # Update environment status
        if destroy_result.success:
            environment.status = "DESTROYED"
            
            # Clear outputs from resources
            for resource in environment.resources:
                resource.outputs = None
                resource.state = "DESTROYED"
        else:
            environment.status = "FAILED"
        
        db.commit()
        
        # If destroy failed, raise exception
        if not destroy_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to destroy environment: {destroy_result.error}"
            )
        
        return environment
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to destroy environment: {str(e)}", environment_id=str(environment_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy environment: {str(e)}"
        ) 