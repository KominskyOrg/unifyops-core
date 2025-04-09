import os
import pytest
import json
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.terraform import Environment, Resource, Connection, EnvironmentStatus, ResourceState
from app.core.terraform import TerraformOperation, TerraformResult, EnvironmentGraph, TerraformService

client = TestClient(app)

# Test data
TEST_ENVIRONMENT_ID = str(uuid4())
TEST_ORGANIZATION_ID = str(uuid4())
TEST_ENVIRONMENT_NAME = "test-environment"
TEST_RESOURCE_ID = str(uuid4())
TEST_RESOURCE_NAME = "test-vpc"
TEST_MODULE_PATH = "aws/vpc"
TEST_VARIABLES = {"vpc_cidr": "10.0.0.0/16", "environment": "test"}


@pytest.fixture
def mock_db_session():
    """Fixture to mock database session."""
    mock_session = MagicMock(spec=Session)
    with patch("app.db.database.get_db", return_value=mock_session):
        yield mock_session


@pytest.fixture
def mock_terraform_service():
    """Fixture to mock the TerraformService."""
    with patch("app.routers.environments.terraform_service") as mock_service:
        mock_service.init = AsyncMock()
        mock_service.plan = AsyncMock()
        mock_service.apply = AsyncMock()
        mock_service.destroy = AsyncMock()
        yield mock_service


@pytest.fixture
def mock_environment_graph():
    """Fixture to mock the EnvironmentGraph."""
    with patch("app.routers.environments.environment_graph") as mock_graph:
        mock_graph.create_environment_config = MagicMock()
        mock_graph.resolve_dependencies = MagicMock()
        yield mock_graph


def create_mock_environment():
    """Create a mock environment object."""
    env = MagicMock(spec=Environment)
    env.id = TEST_ENVIRONMENT_ID
    env.name = TEST_ENVIRONMENT_NAME
    env.description = "Test environment description"
    env.status = EnvironmentStatus.DRAFT.value
    env.organization_id = TEST_ORGANIZATION_ID
    env.team_id = None
    env.created_by = "test-user"
    env.terraform_dir = None
    env.variables = TEST_VARIABLES
    env.tags = {"environment": "test"}
    env.created_at = "2023-05-18T14:30:00Z"
    env.updated_at = "2023-05-18T14:30:00Z"
    env.last_deployed_at = None
    env.estimated_cost = None
    env.resources = []
    env.deployments = []
    return env


def create_mock_resource():
    """Create a mock resource object."""
    resource = MagicMock(spec=Resource)
    resource.id = TEST_RESOURCE_ID
    resource.name = TEST_RESOURCE_NAME
    resource.module_path = TEST_MODULE_PATH
    resource.resource_type = "vpc"
    resource.provider = "aws"
    resource.state = ResourceState.PLANNED.value
    resource.environment_id = TEST_ENVIRONMENT_ID
    resource.variables = TEST_VARIABLES
    resource.outputs = None
    resource.position_x = 100
    resource.position_y = 100
    resource.created_at = "2023-05-18T14:30:00Z"
    resource.updated_at = "2023-05-18T14:30:00Z"
    return resource


def test_create_environment(mock_db_session):
    """Test creating an environment."""
    # Set up mock
    mock_env = create_mock_environment()
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    
    # Mock the created DB object
    with patch("app.models.terraform.Environment", return_value=mock_env):
        # Create request data
        request_data = {
            "name": TEST_ENVIRONMENT_NAME,
            "description": "Test environment description",
            "organization_id": TEST_ORGANIZATION_ID,
            "created_by": "test-user",
            "variables": TEST_VARIABLES,
            "tags": {"environment": "test"}
        }
        
        # Call the endpoint
        response = client.post("/environments/", json=request_data)
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == TEST_ENVIRONMENT_NAME
        assert data["organization_id"] == TEST_ORGANIZATION_ID
        assert data["status"] == EnvironmentStatus.DRAFT.value
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()


def test_list_environments(mock_db_session):
    """Test listing environments."""
    # Set up mock
    mock_env = create_mock_environment()
    mock_db_session.query.return_value.filter.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [mock_env]
    
    # Call the endpoint
    response = client.get("/environments/")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == TEST_ENVIRONMENT_ID
    assert data[0]["name"] == TEST_ENVIRONMENT_NAME


def test_get_environment(mock_db_session):
    """Test getting a single environment."""
    # Set up mock
    mock_env = create_mock_environment()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    
    # Call the endpoint
    response = client.get(f"/environments/{TEST_ENVIRONMENT_ID}")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["name"] == TEST_ENVIRONMENT_NAME
    assert data["organization_id"] == TEST_ORGANIZATION_ID


def test_update_environment(mock_db_session):
    """Test updating an environment."""
    # Set up mock
    mock_env = create_mock_environment()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    
    # Create request data
    request_data = {
        "name": "updated-environment-name",
        "description": "Updated description"
    }
    
    # Call the endpoint
    response = client.put(f"/environments/{TEST_ENVIRONMENT_ID}", json=request_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated-environment-name"
    assert data["description"] == "Updated description"
    
    # Verify database operations
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()


def test_delete_environment(mock_db_session):
    """Test deleting an environment."""
    # Set up mock
    mock_env = create_mock_environment()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.delete.return_value = None
    mock_db_session.commit.return_value = None
    
    # Call the endpoint
    response = client.delete(f"/environments/{TEST_ENVIRONMENT_ID}")
    
    # Check response
    assert response.status_code == 204
    
    # Verify database operations
    mock_db_session.delete.assert_called_once_with(mock_env)
    mock_db_session.commit.assert_called_once()


def test_add_resource(mock_db_session):
    """Test adding a resource to an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_resource = create_mock_resource()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    
    # Mock the created DB object
    with patch("app.models.terraform.Resource", return_value=mock_resource):
        # Create request data
        request_data = {
            "name": TEST_RESOURCE_NAME,
            "module_path": TEST_MODULE_PATH,
            "resource_type": "vpc",
            "provider": "aws",
            "environment_id": TEST_ENVIRONMENT_ID,
            "variables": TEST_VARIABLES,
            "position_x": 100,
            "position_y": 100
        }
        
        # Call the endpoint
        response = client.post(f"/environments/{TEST_ENVIRONMENT_ID}/resources", json=request_data)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == TEST_RESOURCE_NAME
        assert data["module_path"] == TEST_MODULE_PATH
        assert data["environment_id"] == TEST_ENVIRONMENT_ID
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()


def test_generate_terraform(mock_db_session, mock_environment_graph):
    """Test generating Terraform configuration for an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_resource = create_mock_resource()
    mock_env.resources = [mock_resource]
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_resource]
    mock_db_session.commit.return_value = None
    
    # Mock the environment graph
    mock_environment_graph.create_environment_config.return_value = f"environments/env-{TEST_ENVIRONMENT_ID}"
    
    # Call the endpoint
    response = client.post(f"/environments/{TEST_ENVIRONMENT_ID}/generate-terraform")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["terraform_dir"] == f"environments/env-{TEST_ENVIRONMENT_ID}"
    
    # Verify environment graph was called correctly
    mock_environment_graph.create_environment_config.assert_called_once_with(
        modules=[TEST_MODULE_PATH],
        variables={TEST_MODULE_PATH: TEST_VARIABLES},
        environment_name=f"env-{TEST_ENVIRONMENT_ID}"
    )
    
    # Verify database operations
    mock_db_session.commit.assert_called_once()


def test_deploy_environment(mock_db_session, mock_terraform_service):
    """Test deploying an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_env.terraform_dir = f"environments/env-{TEST_ENVIRONMENT_ID}"
    mock_resource = create_mock_resource()
    mock_env.resources = [mock_resource]
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    
    # Mock Terraform service responses
    init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="init-12345"
    )
    apply_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete! Resources: 1 added, 0 changed, 0 destroyed.",
        duration_ms=500,
        execution_id="apply-12345",
        outputs={
            "test_vpc_id": {
                "value": "vpc-12345",
                "type": "string"
            }
        }
    )
    mock_terraform_service.init.return_value = init_result
    mock_terraform_service.apply.return_value = apply_result
    
    # Create request data
    request_data = {
        "auto_approve": True,
        "variables": None
    }
    
    # Call the endpoint
    response = client.post(f"/environments/{TEST_ENVIRONMENT_ID}/deploy", json=request_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["status"] == "DEPLOYED"
    
    # Verify Terraform service calls
    mock_terraform_service.init.assert_called_once_with(mock_env.terraform_dir)
    mock_terraform_service.apply.assert_called_once_with(
        module_path=mock_env.terraform_dir,
        variables=None,
        auto_approve=True
    )


def test_destroy_environment(mock_db_session, mock_terraform_service):
    """Test destroying an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_env.terraform_dir = f"environments/env-{TEST_ENVIRONMENT_ID}"
    mock_resource = create_mock_resource()
    mock_env.resources = [mock_resource]
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    
    # Mock Terraform service responses
    init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="init-12345"
    )
    destroy_result = TerraformResult(
        operation=TerraformOperation.DESTROY,
        success=True,
        output="Destroy complete! Resources: 1 destroyed.",
        duration_ms=300,
        execution_id="destroy-12345"
    )
    mock_terraform_service.init.return_value = init_result
    mock_terraform_service.destroy.return_value = destroy_result
    
    # Call the endpoint with auto_approve=True
    response = client.post(f"/environments/{TEST_ENVIRONMENT_ID}/destroy?auto_approve=true")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["status"] == "DESTROYED"
    
    # Verify Terraform service calls
    mock_terraform_service.init.assert_called_once_with(mock_env.terraform_dir)
    mock_terraform_service.destroy.assert_called_once_with(
        module_path=mock_env.terraform_dir,
        auto_approve=True
    )
    
    # Verify resources were updated
    assert mock_resource.outputs is None
    assert mock_resource.state == "DESTROYED"


def test_environment_not_found(mock_db_session):
    """Test handling of environment not found."""
    # Set up mock to return None for the environment
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Call the endpoint
    response = client.get(f"/environments/{TEST_ENVIRONMENT_ID}")
    
    # Check response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower() 