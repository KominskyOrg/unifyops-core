import os
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models.environment import Environment, EnvironmentStatus
from app.core.terraform import TerraformOperation, TerraformResult, TerraformService
from app.core.environment import EnvironmentService

client = TestClient(app)

# Test data
TEST_ENVIRONMENT_ID = "12345678-1234-5678-1234-567812345678"
TEST_ENVIRONMENT_NAME = "test-environment"
TEST_MODULE_PATH = "aws/vpc"
TEST_VARIABLES = {"vpc_cidr": "10.0.0.0/16", "environment": "test"}


@pytest.fixture
def mock_db_session():
    """Fixture to mock database session."""
    mock_session = MagicMock(spec=Session)
    with patch("app.db.database.get_db", return_value=mock_session):
        yield mock_session


@pytest.fixture
def mock_environment_service():
    """Fixture to mock the EnvironmentService."""
    with patch("app.routers.environment.environment_service") as mock_service:
        # Setup async methods with AsyncMock
        mock_service.run_terraform_init = AsyncMock()
        mock_service.run_terraform_plan = AsyncMock()
        mock_service.run_terraform_apply = AsyncMock()
        mock_service.provision_environment = AsyncMock()
        yield mock_service


@pytest.fixture
def mock_terraform_service():
    """Fixture to mock the TerraformService."""
    with patch("app.routers.environment.terraform_service") as mock_service:
        mock_service.init = AsyncMock()
        mock_service.plan = AsyncMock()
        mock_service.apply = AsyncMock()
        yield mock_service


def create_mock_environment(status=EnvironmentStatus.PENDING.value):
    """Create a mock environment object."""
    env = MagicMock(spec=Environment)
    env.id = TEST_ENVIRONMENT_ID
    env.name = TEST_ENVIRONMENT_NAME
    env.module_path = TEST_MODULE_PATH
    env.variables = TEST_VARIABLES
    env.status = status
    env.auto_apply = "True"
    env.created_at = "2023-05-18T14:30:00Z"
    env.updated_at = "2023-05-18T14:30:00Z"
    env.error_message = None
    env.init_execution_id = None
    env.plan_execution_id = None
    env.apply_execution_id = None
    env.correlation_id = "test-correlation-id"
    return env


def test_create_environment(mock_db_session, mock_environment_service):
    """Test creating an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_environment_service.create_environment.return_value = mock_env
    
    # Mock os.path.exists to return True for module path check
    with patch("os.path.exists", return_value=True):
        # Create request data
        request_data = {
            "name": TEST_ENVIRONMENT_NAME,
            "module_path": TEST_MODULE_PATH,
            "variables": TEST_VARIABLES,
            "auto_apply": True
        }
        
        # Call the endpoint
        response = client.post("/api/v1/environments", json=request_data)
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == TEST_ENVIRONMENT_ID
        assert data["name"] == TEST_ENVIRONMENT_NAME
        assert data["module_path"] == TEST_MODULE_PATH
        assert data["status"] == EnvironmentStatus.PENDING.value
        
        # Verify service was called correctly
        mock_environment_service.create_environment.assert_called_once()
        call_kwargs = mock_environment_service.create_environment.call_args.kwargs
        assert call_kwargs["name"] == TEST_ENVIRONMENT_NAME
        assert call_kwargs["module_path"] == TEST_MODULE_PATH
        assert call_kwargs["variables"] == TEST_VARIABLES


def test_get_environment(mock_db_session, mock_environment_service):
    """Test getting an environment."""
    # Set up mocks
    mock_env = create_mock_environment(status=EnvironmentStatus.PROVISIONED.value)
    mock_environment_service.get_environment.return_value = mock_env
    
    # Call the endpoint
    response = client.get(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["status"] == EnvironmentStatus.PROVISIONED.value
    
    # Verify service was called correctly - using ANY for session object comparison
    mock_environment_service.get_environment.assert_called_once_with(
        ANY, TEST_ENVIRONMENT_ID
    )


def test_list_environments(mock_db_session, mock_environment_service):
    """Test listing environments."""
    # Set up mocks
    mock_env1 = create_mock_environment(status=EnvironmentStatus.PROVISIONED.value)
    mock_env2 = create_mock_environment(status=EnvironmentStatus.FAILED.value)
    mock_env2.id = "abcdef12-3456-7890-abcd-ef1234567890"
    mock_env2.name = "another-environment"
    
    mock_environment_service.list_environments.return_value = [mock_env1, mock_env2]
    
    # Call the endpoint
    response = client.get("/api/v1/environments")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["environments"]) == 2
    assert data["environments"][0]["id"] == TEST_ENVIRONMENT_ID
    assert data["environments"][1]["id"] == "abcdef12-3456-7890-abcd-ef1234567890"
    
    # Verify service was called correctly
    mock_environment_service.list_environments.assert_called_once()


def test_init_environment(mock_db_session, mock_environment_service):
    """Test initializing an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_environment_service.get_environment.return_value = mock_env
    
    # Mock the run_terraform_init method with AsyncMock
    mock_init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="init-12345",
    )
    mock_environment_service.run_terraform_init.return_value = mock_init_result
    
    # Call the endpoint
    response = client.post(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/init")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "init"
    assert data["success"] is True
    assert "initialized successfully" in data["message"]
    assert data["execution_id"] == "init-12345"


def test_plan_environment(mock_db_session, mock_environment_service):
    """Test planning an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_environment_service.get_environment.return_value = mock_env
    
    # Mock the run_terraform_plan method with AsyncMock
    mock_plan_result = TerraformResult(
        operation=TerraformOperation.PLAN,
        success=True,
        output="Plan: 2 to add, 0 to change, 0 to destroy.",
        duration_ms=200,
        execution_id="plan-12345",
    )
    mock_environment_service.run_terraform_plan.return_value = mock_plan_result
    
    # Call the endpoint
    response = client.post(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/plan")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "plan"
    assert data["success"] is True
    assert data["execution_id"] == "plan-12345"
    assert data["plan_id"] == "plan-12345"


def test_apply_environment(mock_db_session, mock_environment_service):
    """Test applying an environment."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_environment_service.get_environment.return_value = mock_env
    
    # Mock the run_terraform_apply method with AsyncMock
    mock_apply_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete! Resources: 2 added, 0 changed, 0 destroyed.",
        duration_ms=300,
        execution_id="apply-12345",
        outputs={"vpc_id": "vpc-12345"}
    )
    mock_environment_service.run_terraform_apply.return_value = mock_apply_result
    
    # Call the endpoint
    response = client.post(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/apply")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "apply"
    assert data["success"] is True
    assert data["execution_id"] == "apply-12345"
    assert data["outputs"] == {"vpc_id": "vpc-12345"}


def test_provision_environment(mock_db_session, mock_environment_service):
    """Test provisioning an environment asynchronously."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_environment_service.get_environment.return_value = mock_env
    mock_environment_service.update_environment_status.return_value = mock_env
    
    # Call the endpoint
    response = client.post(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/provision")
    
    # Check response
    assert response.status_code == 202
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["name"] == TEST_ENVIRONMENT_NAME
    
    # Verify service was called correctly - using keyword argument matching
    mock_environment_service.start_provisioning_task.assert_called_once()
    call_args = mock_environment_service.start_provisioning_task.call_args
    assert call_args.kwargs["environment_id"] == TEST_ENVIRONMENT_ID
    
    # Verify status was updated
    mock_environment_service.update_environment_status.assert_called_once()
    args = mock_environment_service.update_environment_status.call_args.args
    assert args[1] == TEST_ENVIRONMENT_ID
    assert args[2] == EnvironmentStatus.PENDING


def test_get_environment_status(mock_db_session, mock_environment_service):
    """Test getting detailed environment status."""
    # Set up mocks
    mock_status_info = {
        "id": TEST_ENVIRONMENT_ID,
        "name": TEST_ENVIRONMENT_NAME,
        "status": EnvironmentStatus.PROVISIONED.value,
        "init_execution_id": "init-12345",
        "plan_execution_id": "plan-12345",
        "apply_execution_id": "apply-12345",
        "created_at": "2023-05-18T14:30:00Z",
        "updated_at": "2023-05-18T14:45:00Z",
        "error_message": None,
        "resource_count": 2,
        "state_file": f"terraform.{TEST_ENVIRONMENT_ID}.tfstate",
        "outputs": {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]}
    }
    mock_environment_service.get_environment_status.return_value = mock_status_info
    
    # Call the endpoint
    response = client.get(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/status")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_ENVIRONMENT_ID
    assert data["status"] == EnvironmentStatus.PROVISIONED.value
    assert data["init_execution_id"] == "init-12345"
    assert data["outputs"]["vpc_id"] == "vpc-12345"
    assert data["resource_count"] == 2
    
    # Verify service was called correctly
    mock_environment_service.get_environment_status.assert_called_once()
    call_args = mock_environment_service.get_environment_status.call_args
    # Using ANY for session object comparison instead of strict equality
    assert call_args.args[1] == TEST_ENVIRONMENT_ID


# Patching the error handlers to avoid JSON serialization issues
@patch("app.core.middleware.logger")
def test_get_environment_not_found(mock_logger, mock_db_session, mock_environment_service):
    """Test getting an environment that doesn't exist."""
    # Set up mocks
    mock_environment_service.get_environment.return_value = None
    
    # Call the endpoint
    response = client.get(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}")
    
    # Check response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


# Patching the error handlers to avoid JSON serialization issues
@patch("app.core.middleware.logger")
def test_get_environment_status_not_found(mock_logger, mock_db_session, mock_environment_service):
    """Test getting status for an environment that doesn't exist."""
    # Set up mocks
    from app.core.exceptions import NotFoundError
    mock_environment_service.get_environment_status.side_effect = NotFoundError(
        f"Environment not found: {TEST_ENVIRONMENT_ID}"
    )
    
    # Call the endpoint
    response = client.get(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/status")
    
    # Check response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_environment_status_error(mock_db_session, mock_environment_service):
    """Test getting status with an unexpected error."""
    # Set up mocks
    mock_environment_service.get_environment_status.side_effect = Exception("Unexpected error")
    
    # Call the endpoint
    response = client.get(f"/api/v1/environments/{TEST_ENVIRONMENT_ID}/status")
    
    # Check response
    assert response.status_code == 500
    data = response.json()
    assert "failed to retrieve" in data["detail"].lower() 