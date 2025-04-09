import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError

from app.schemas.terraform import (
    ResourceBase,
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ConnectionBase,
    ConnectionCreate,
    ConnectionResponse,
    EnvironmentBase,
    EnvironmentCreate,
    EnvironmentUpdate,
    EnvironmentResponse,
    DeploymentBase,
    DeploymentCreate,
    DeploymentResponse,
    OrganizationBase,
    OrganizationCreate,
    OrganizationResponse,
    TeamBase,
    TeamCreate,
    TeamResponse,
    ResourcePositionUpdate,
    GenerateTerraformRequest,
    DeployEnvironmentRequest,
    ApplyModuleRequest,
    TemplateVariableResponse,
    TemplateOutputResponse,
    TemplateDetailsResponse,
    CreateModuleFromTemplateRequest
)
from app.models.terraform import (
    EnvironmentStatus,
    ResourceState,
    ConnectionType,
    DeploymentStatus
)


def test_resource_base_schema():
    """Test the ResourceBase schema validation."""
    # Valid data
    valid_data = {
        "name": "Test Resource",
        "module_path": "aws/vpc",
        "resource_type": "vpc",
        "provider": "aws",
        "variables": {"vpc_cidr": "10.0.0.0/16"},
        "position_x": 100,
        "position_y": 100
    }
    resource = ResourceBase(**valid_data)
    assert resource.name == "Test Resource"
    assert resource.module_path == "aws/vpc"
    assert resource.resource_type == "vpc"
    assert resource.provider == "aws"
    assert resource.variables == {"vpc_cidr": "10.0.0.0/16"}
    assert resource.position_x == 100
    assert resource.position_y == 100
    
    # Missing required fields
    with pytest.raises(ValidationError):
        ResourceBase(
            name="Test Resource",
            # missing module_path
            resource_type="vpc",
            provider="aws"
        )
    
    # Invalid position values (negative)
    with pytest.raises(ValidationError):
        ResourceBase(
            name="Test Resource",
            module_path="aws/vpc",
            resource_type="vpc",
            provider="aws",
            position_x=-1,
            position_y=100
        )


def test_resource_create_schema():
    """Test the ResourceCreate schema validation."""
    # Valid data
    valid_data = {
        "name": "Test Resource",
        "module_path": "aws/vpc",
        "resource_type": "vpc",
        "provider": "aws",
        "variables": {"vpc_cidr": "10.0.0.0/16"},
        "position_x": 100,
        "position_y": 100,
        "environment_id": str(uuid.uuid4())
    }
    resource = ResourceCreate(**valid_data)
    assert resource.name == "Test Resource"
    assert resource.environment_id is not None
    
    # Missing environment_id
    with pytest.raises(ValidationError):
        ResourceCreate(
            name="Test Resource",
            module_path="aws/vpc",
            resource_type="vpc",
            provider="aws",
            # missing environment_id
        )


def test_resource_update_schema():
    """Test the ResourceUpdate schema validation."""
    # All fields are optional in the update schema
    update_data = {
        "name": "Updated Resource",
        "variables": {"vpc_cidr": "10.0.0.0/16", "tags": {"Name": "MyVPC"}},
        "position_x": 150,
        "position_y": 200
    }
    resource_update = ResourceUpdate(**update_data)
    assert resource_update.name == "Updated Resource"
    assert resource_update.variables == {"vpc_cidr": "10.0.0.0/16", "tags": {"Name": "MyVPC"}}
    assert resource_update.position_x == 150
    assert resource_update.position_y == 200
    
    # Empty update should be valid
    empty_update = ResourceUpdate()
    assert empty_update.dict(exclude_unset=True) == {}
    
    # Invalid position values
    with pytest.raises(ValidationError):
        ResourceUpdate(position_x=-10)


def test_resource_response_schema():
    """Test the ResourceResponse schema."""
    resource_id = str(uuid.uuid4())
    environment_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    response_data = {
        "id": resource_id,
        "name": "Test Resource",
        "module_path": "aws/vpc",
        "resource_type": "vpc",
        "provider": "aws",
        "state": ResourceState.PLANNED.value,
        "variables": {"vpc_cidr": "10.0.0.0/16"},
        "outputs": {"vpc_id": "vpc-12345"},
        "position_x": 100,
        "position_y": 100,
        "environment_id": environment_id,
        "created_at": created_at,
        "updated_at": updated_at
    }
    
    resource_response = ResourceResponse(**response_data)
    assert str(resource_response.id) == resource_id
    assert resource_response.name == "Test Resource"
    assert resource_response.state == ResourceState.PLANNED.value
    assert resource_response.outputs == {"vpc_id": "vpc-12345"}
    assert str(resource_response.environment_id) == environment_id
    assert resource_response.created_at == created_at
    assert resource_response.updated_at == updated_at


def test_connection_schemas():
    """Test the Connection schemas."""
    source_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    connection_id = str(uuid.uuid4())
    
    # Test ConnectionBase
    base_data = {
        "source_id": source_id,
        "target_id": target_id,
        "connection_type": ConnectionType.NETWORK.value,
        "name": "VPC to Subnet",
        "configuration": {"subnet_cidr": "10.0.1.0/24"}
    }
    
    connection_base = ConnectionBase(**base_data)
    assert str(connection_base.source_id) == source_id
    assert str(connection_base.target_id) == target_id
    assert connection_base.connection_type == ConnectionType.NETWORK.value
    assert connection_base.name == "VPC to Subnet"
    assert connection_base.configuration == {"subnet_cidr": "10.0.1.0/24"}
    
    # Test ConnectionCreate - same as ConnectionBase
    connection_create = ConnectionCreate(**base_data)
    assert str(connection_create.source_id) == source_id
    
    # Test ConnectionResponse
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    response_data = {
        **base_data,
        "id": connection_id,
        "created_at": created_at,
        "updated_at": updated_at
    }
    
    connection_response = ConnectionResponse(**response_data)
    assert str(connection_response.id) == connection_id
    assert str(connection_response.source_id) == source_id
    assert str(connection_response.target_id) == target_id
    assert connection_response.created_at == created_at
    assert connection_response.updated_at == updated_at


def test_environment_schemas():
    """Test the Environment schemas."""
    org_id = str(uuid.uuid4())
    team_id = str(uuid.uuid4())
    env_id = str(uuid.uuid4())
    
    # Test EnvironmentBase
    base_data = {
        "name": "Test Environment",
        "description": "Test Environment Description",
        "variables": {"region": "us-west-2"},
        "tags": {"environment": "test"},
        "organization_id": org_id
    }
    
    env_base = EnvironmentBase(**base_data)
    assert env_base.name == "Test Environment"
    assert env_base.description == "Test Environment Description"
    assert env_base.variables == {"region": "us-west-2"}
    assert env_base.tags == {"environment": "test"}
    
    # Test EnvironmentCreate
    create_data = {
        **base_data,
        "organization_id": org_id,
        "team_id": team_id,
        "created_by": "test-user"
    }
    
    env_create = EnvironmentCreate(**create_data)
    assert env_create.name == "Test Environment"
    assert str(env_create.organization_id) == org_id
    assert str(env_create.team_id) == team_id
    
    # Test EnvironmentUpdate
    update_data = {
        "name": "Updated Environment",
        "variables": {"region": "us-east-1"},
        "tags": {"environment": "test", "updated": "true"}
    }
    
    env_update = EnvironmentUpdate(**update_data)
    assert env_update.name == "Updated Environment"
    assert env_update.variables == {"region": "us-east-1"}
    assert env_update.tags == {"environment": "test", "updated": "true"}
    
    # Empty update should be valid
    empty_update = EnvironmentUpdate()
    assert empty_update.dict(exclude_unset=True) == {}
    
    # Test EnvironmentResponse
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    response_data = {
        **create_data,
        "id": env_id,
        "status": EnvironmentStatus.DRAFT.value,
        "created_by": "test-user",
        "created_at": created_at,
        "updated_at": updated_at,
        "resources": [],
        "connections": []
    }
    
    env_response = EnvironmentResponse(**response_data)
    assert str(env_response.id) == env_id
    assert env_response.name == "Test Environment"
    assert env_response.status == EnvironmentStatus.DRAFT.value
    assert env_response.created_by == "test-user"
    assert str(env_response.organization_id) == org_id
    assert str(env_response.team_id) == team_id
    assert env_response.created_at == created_at
    assert env_response.updated_at == updated_at
    assert env_response.resources == []
    assert env_response.connections == []


def test_deployment_schemas():
    """Test the Deployment schemas."""
    env_id = str(uuid.uuid4())
    deployment_id = str(uuid.uuid4())
    execution_id = str(uuid.uuid4())
    
    # Test DeploymentBase
    base_data = {
        "environment_id": env_id,
        "execution_id": execution_id,
        "operation": "apply",
        "status": DeploymentStatus.RUNNING.value,
        "initiated_by": "test-user"
    }
    
    deployment_base = DeploymentBase(**base_data)
    assert str(deployment_base.environment_id) == env_id
    assert deployment_base.execution_id == execution_id
    assert deployment_base.operation == "apply"
    assert deployment_base.status == DeploymentStatus.RUNNING.value
    assert deployment_base.initiated_by == "test-user"
    
    # Test DeploymentCreate
    create_data = {
        "environment_id": env_id,
        "operation": "apply",
        "initiated_by": "test-user"
    }
    
    deployment_create = DeploymentCreate(**create_data)
    assert str(deployment_create.environment_id) == env_id
    assert deployment_create.operation == "apply"
    assert deployment_create.initiated_by == "test-user"
    
    # Test DeploymentResponse
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    completed_at = datetime.utcnow()
    
    response_data = {
        **base_data,
        "id": deployment_id,
        "output": "Apply complete!",
        "error": None,
        "created_at": created_at,
        "updated_at": updated_at,
        "completed_at": completed_at,
        "started_at": created_at
    }
    
    deployment_response = DeploymentResponse(**response_data)
    assert str(deployment_response.id) == deployment_id
    assert str(deployment_response.environment_id) == env_id
    assert deployment_response.execution_id == execution_id
    assert deployment_response.operation == "apply"
    assert deployment_response.status == DeploymentStatus.RUNNING.value
    assert deployment_response.output == "Apply complete!"
    assert deployment_response.error is None
    assert deployment_response.created_at == created_at
    assert deployment_response.updated_at == updated_at
    assert deployment_response.completed_at == completed_at


def test_organization_and_team_schemas():
    """Test the Organization and Team schemas."""
    org_id = str(uuid.uuid4())
    team_id = str(uuid.uuid4())
    
    # Test OrganizationBase
    org_base_data = {
        "name": "Test Organization",
        "description": "Test Organization Description"
    }
    
    org_base = OrganizationBase(**org_base_data)
    assert org_base.name == "Test Organization"
    assert org_base.description == "Test Organization Description"
    
    # Test OrganizationCreate - same as OrganizationBase
    org_create = OrganizationCreate(**org_base_data)
    assert org_create.name == "Test Organization"
    
    # Test OrganizationResponse
    created_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    
    org_response_data = {
        **org_base_data,
        "id": org_id,
        "created_at": created_at,
        "updated_at": updated_at
    }
    
    org_response = OrganizationResponse(**org_response_data)
    assert str(org_response.id) == org_id
    assert org_response.name == "Test Organization"
    assert org_response.created_at == created_at
    assert org_response.updated_at == updated_at
    
    # Test TeamBase
    team_base_data = {
        "name": "Test Team",
        "description": "Test Team Description",
        "organization_id": org_id
    }
    
    team_base = TeamBase(**team_base_data)
    assert team_base.name == "Test Team"
    assert team_base.description == "Test Team Description"
    
    # Test TeamCreate
    team_create_data = {
        **team_base_data,
        "organization_id": org_id
    }
    
    team_create = TeamCreate(**team_create_data)
    assert team_create.name == "Test Team"
    assert str(team_create.organization_id) == org_id
    
    # Test TeamResponse
    team_response_data = {
        **team_create_data,
        "id": team_id,
        "created_at": created_at,
        "updated_at": updated_at
    }
    
    team_response = TeamResponse(**team_response_data)
    assert str(team_response.id) == team_id
    assert team_response.name == "Test Team"
    assert str(team_response.organization_id) == org_id
    assert team_response.created_at == created_at
    assert team_response.updated_at == updated_at


def test_resource_position_update_schema():
    """Test the ResourcePositionUpdate schema."""
    position_data = {
        "position_x": 100,
        "position_y": 200
    }
    
    position_update = ResourcePositionUpdate(**position_data)
    assert position_update.position_x == 100
    assert position_update.position_y == 200
    
    # Test that negative values are not allowed
    with pytest.raises(ValidationError):
        ResourcePositionUpdate(position_x=-100, position_y=200)
    
    with pytest.raises(ValidationError):
        ResourcePositionUpdate(position_x=100, position_y=-200)


def test_generate_terraform_request_schema():
    """Test the GenerateTerraformRequest schema."""
    env_id = str(uuid.uuid4())
    
    request_data = {
        "environment_id": env_id,
        "pretty_print": True
    }
    
    gen_request = GenerateTerraformRequest(**request_data)
    assert str(gen_request.environment_id) == env_id
    assert gen_request.pretty_print is True
    
    # Test with default value for pretty_print
    default_request = GenerateTerraformRequest(environment_id=env_id)
    assert str(default_request.environment_id) == env_id
    assert default_request.pretty_print is False


def test_deploy_environment_request_schema():
    """Test the DeployEnvironmentRequest schema."""
    env_id = str(uuid.uuid4())
    
    request_data = {
        "environment_id": env_id,
        "initiated_by": "test-user"
    }
    
    deploy_request = DeployEnvironmentRequest(**request_data)
    assert str(deploy_request.environment_id) == env_id
    assert deploy_request.initiated_by == "test-user"
    
    # Test without initiated_by (should default to "system")
    default_request = DeployEnvironmentRequest(environment_id=env_id)
    assert str(default_request.environment_id) == env_id
    assert default_request.initiated_by == "system"


def test_apply_module_request_schema():
    """Test the ApplyModuleRequest schema."""
    env_id = str(uuid.uuid4())
    
    request_data = {
        "environment_id": env_id,
        "module_path": "aws/vpc",
        "variables": {"vpc_cidr": "10.0.0.0/16"}
    }
    
    apply_request = ApplyModuleRequest(**request_data)
    assert str(apply_request.environment_id) == env_id
    assert apply_request.module_path == "aws/vpc"
    assert apply_request.variables == {"vpc_cidr": "10.0.0.0/16"}


def test_template_schemas():
    """Test the Template-related schemas."""
    # Test TemplateVariableResponse
    var_data = {
        "name": "vpc_cidr",
        "type": "string",
        "description": "CIDR block for the VPC",
        "default": "10.0.0.0/16",
        "required": True
    }
    
    var_response = TemplateVariableResponse(**var_data)
    assert var_response.name == "vpc_cidr"
    assert var_response.type == "string"
    assert var_response.description == "CIDR block for the VPC"
    assert var_response.default == "10.0.0.0/16"
    assert var_response.required is True
    
    # Test TemplateOutputResponse
    output_data = {
        "name": "vpc_id",
        "description": "ID of the VPC",
        "value": "${aws_vpc.main.id}"
    }
    
    output_response = TemplateOutputResponse(**output_data)
    assert output_response.name == "vpc_id"
    assert output_response.description == "ID of the VPC"
    assert output_response.value == "${aws_vpc.main.id}"
    
    # Test TemplateDetailsResponse
    template_data = {
        "name": "aws_vpc",
        "description": "AWS VPC Template",
        "provider": "aws",
        "variables": [var_data],
        "outputs": [output_data],
        "resource_types": ["vpc", "subnet", "internet_gateway"]
    }
    
    template_response = TemplateDetailsResponse(**template_data)
    assert template_response.name == "aws_vpc"
    assert template_response.description == "AWS VPC Template"
    assert template_response.provider == "aws"
    assert len(template_response.variables) == 1
    assert template_response.variables[0].name == "vpc_cidr"
    assert len(template_response.outputs) == 1
    assert template_response.outputs[0].name == "vpc_id"
    assert template_response.resource_types == ["vpc", "subnet", "internet_gateway"]
    
    # Test CreateModuleFromTemplateRequest
    request_data = {
        "template_name": "aws_vpc",
        "module_name": "my_vpc_module",
        "variables": {"vpc_cidr": "10.0.0.0/16"}
    }
    
    create_request = CreateModuleFromTemplateRequest(**request_data)
    assert create_request.template_name == "aws_vpc"
    assert create_request.module_name == "my_vpc_module"
    assert create_request.variables == {"vpc_cidr": "10.0.0.0/16"} 