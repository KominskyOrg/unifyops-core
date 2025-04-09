import os
import asyncio
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session

from app.core.environment import EnvironmentService
from app.core.terraform import TerraformService, TerraformOperation, TerraformResult
from app.models.environment import Environment, EnvironmentStatus
from app.core.exceptions import NotFoundError

# Test data
TEST_ENVIRONMENT_ID = "12345678-1234-5678-1234-567812345678"
TEST_ENVIRONMENT_NAME = "test-environment"
TEST_MODULE_PATH = "aws/vpc"
TEST_VARIABLES = {"vpc_cidr": "10.0.0.0/16", "environment": "test"}


@pytest.fixture
def mock_db_session():
    """Fixture to mock database session."""
    mock_session = MagicMock(spec=Session)
    # Setup query to return a query object that can be filtered
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_session.query.return_value = mock_query
    return mock_session


@pytest.fixture
def mock_terraform_service():
    """Fixture to mock TerraformService."""
    mock_service = MagicMock(spec=TerraformService)
    mock_service.base_dir = "/tmp"
    mock_service.init = AsyncMock()
    mock_service.plan = AsyncMock()
    mock_service.apply = AsyncMock()
    mock_service.output = AsyncMock()
    return mock_service


@pytest.fixture
def environment_service(mock_terraform_service):
    """Fixture to create EnvironmentService with mocked dependencies."""
    return EnvironmentService(mock_terraform_service)


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


def test_create_environment(mock_db_session, environment_service):
    """Test creating an environment."""
    # Set up mocks
    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()
    
    # Call the method
    with patch("uuid.uuid4", return_value=TEST_ENVIRONMENT_ID):
        result = environment_service.create_environment(
            db=mock_db_session,
            name=TEST_ENVIRONMENT_NAME,
            module_path=TEST_MODULE_PATH,
            variables=TEST_VARIABLES,
            auto_apply=True,
            correlation_id="test-correlation-id"
        )
    
    # Verify result
    assert result.id == TEST_ENVIRONMENT_ID
    assert result.name == TEST_ENVIRONMENT_NAME
    assert result.module_path == TEST_MODULE_PATH
    assert result.variables == TEST_VARIABLES
    assert result.status == EnvironmentStatus.PENDING.value
    assert result.auto_apply == "True"
    
    # Verify DB operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()


def test_get_environment(mock_db_session, environment_service):
    """Test getting an environment by ID."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_env
    
    # Call the method
    result = environment_service.get_environment(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify result
    assert result == mock_env
    
    # Verify DB query
    mock_db_session.query.assert_called_once_with(Environment)
    mock_db_session.query.return_value.filter.assert_called_once()


def test_list_environments(mock_db_session, environment_service):
    """Test listing environments."""
    # Set up mocks
    mock_envs = [create_mock_environment(), create_mock_environment(EnvironmentStatus.PROVISIONED.value)]
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_envs
    
    # Call the method
    result = environment_service.list_environments(mock_db_session)
    
    # Verify result
    assert result == mock_envs
    assert len(result) == 2
    
    # Verify DB query
    mock_db_session.query.assert_called_once_with(Environment)
    mock_db_session.query.return_value.order_by.assert_called_once()
    mock_db_session.query.return_value.order_by.return_value.offset.assert_called_once_with(0)
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.assert_called_once_with(100)


def test_update_environment_status(mock_db_session, environment_service):
    """Test updating environment status."""
    # Set up mocks
    mock_env = create_mock_environment()
    environment_service.get_environment = MagicMock(return_value=mock_env)
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()
    
    # Call the method
    result = environment_service.update_environment_status(
        mock_db_session, 
        TEST_ENVIRONMENT_ID, 
        EnvironmentStatus.PROVISIONED,
        error_message=None
    )
    
    # Verify result
    assert result == mock_env
    assert mock_env.status == EnvironmentStatus.PROVISIONED.value
    assert mock_env.error_message is None
    
    # Verify DB operations
    environment_service.get_environment.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_env)


def test_update_environment_status_not_found(mock_db_session, environment_service):
    """Test updating status for non-existent environment."""
    # Set up mocks
    environment_service.get_environment = MagicMock(return_value=None)
    
    # Call the method and check for exception
    with pytest.raises(NotFoundError):
        environment_service.update_environment_status(
            mock_db_session, 
            TEST_ENVIRONMENT_ID, 
            EnvironmentStatus.PROVISIONED
        )


def test_update_environment_execution(mock_db_session, environment_service):
    """Test updating environment execution IDs."""
    # Set up mocks
    mock_env = create_mock_environment()
    environment_service.get_environment = MagicMock(return_value=mock_env)
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()
    
    # Test init execution ID
    result = environment_service.update_environment_execution(
        mock_db_session,
        TEST_ENVIRONMENT_ID,
        TerraformOperation.INIT,
        "init-12345"
    )
    
    # Verify result
    assert result == mock_env
    assert mock_env.init_execution_id == "init-12345"
    
    # Test plan execution ID
    result = environment_service.update_environment_execution(
        mock_db_session,
        TEST_ENVIRONMENT_ID,
        TerraformOperation.PLAN,
        "plan-12345"
    )
    
    # Verify result
    assert result == mock_env
    assert mock_env.plan_execution_id == "plan-12345"
    
    # Test apply execution ID
    result = environment_service.update_environment_execution(
        mock_db_session,
        TEST_ENVIRONMENT_ID,
        TerraformOperation.APPLY,
        "apply-12345"
    )
    
    # Verify result
    assert result == mock_env
    assert mock_env.apply_execution_id == "apply-12345"


@pytest.mark.asyncio
async def test_run_terraform_init(mock_db_session, environment_service, mock_terraform_service):
    """Test running terraform init."""
    # Set up mocks
    mock_env = create_mock_environment()
    environment_service.get_environment = MagicMock(return_value=mock_env)
    environment_service.update_environment_status = MagicMock()
    environment_service.update_environment_execution = MagicMock()
    
    # Mock terraform init result
    mock_init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="init-12345",
    )
    mock_terraform_service.init.return_value = mock_init_result
    
    # Call the method
    result = await environment_service.run_terraform_init(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify result
    assert result == mock_init_result
    
    # Verify method calls
    environment_service.get_environment.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.update_environment_status.assert_called()
    assert environment_service.update_environment_status.call_count == 2
    environment_service.update_environment_execution.assert_called_once()
    
    # Verify terraform service call
    mock_terraform_service.init.assert_called_once()
    args, kwargs = mock_terraform_service.init.call_args
    assert kwargs["module_path"] == TEST_MODULE_PATH
    assert "backend_config" in kwargs


@pytest.mark.asyncio
async def test_run_terraform_init_failed(mock_db_session, environment_service, mock_terraform_service):
    """Test handling failed terraform init."""
    # Set up mocks
    mock_env = create_mock_environment()
    environment_service.get_environment = MagicMock(return_value=mock_env)
    environment_service.update_environment_status = MagicMock()
    environment_service.update_environment_execution = MagicMock()
    
    # Mock terraform init result with failure
    mock_init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=False,
        output="",
        error="Error initializing terraform",
        duration_ms=100,
        execution_id="init-12345",
    )
    mock_terraform_service.init.return_value = mock_init_result
    
    # Call the method
    result = await environment_service.run_terraform_init(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify result
    assert result == mock_init_result
    assert result.success is False
    
    # Verify method calls
    environment_service.update_environment_status.assert_called()
    calls = environment_service.update_environment_status.call_args_list
    # Check the last call was to update status to FAILED
    last_call = calls[-1]
    assert last_call.args[2] == EnvironmentStatus.FAILED
    # Check error message either in args[3] or kwargs
    error_message = ""
    if len(last_call.args) > 3:
        error_message = last_call.args[3]
    else:
        error_message = last_call.kwargs.get("error_message", "")
    assert "Error initializing terraform" in error_message


@pytest.mark.asyncio
async def test_run_terraform_plan(mock_db_session, environment_service, mock_terraform_service):
    """Test running terraform plan."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_env.init_execution_id = "init-12345"  # Already initialized
    environment_service.get_environment = MagicMock(return_value=mock_env)
    environment_service.update_environment_status = MagicMock()
    environment_service.update_environment_execution = MagicMock()
    
    # Mock terraform plan result
    mock_plan_result = TerraformResult(
        operation=TerraformOperation.PLAN,
        success=True,
        output="Plan: 2 to add, 0 to change, 0 to destroy.",
        duration_ms=200,
        execution_id="plan-12345",
    )
    mock_terraform_service.plan.return_value = mock_plan_result
    
    # Call the method
    result = await environment_service.run_terraform_plan(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify result
    assert result == mock_plan_result
    
    # Verify method calls
    environment_service.get_environment.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.update_environment_status.assert_called_once_with(
        mock_db_session, TEST_ENVIRONMENT_ID, EnvironmentStatus.PLANNING
    )
    environment_service.update_environment_execution.assert_called_once()
    
    # Verify terraform service call
    mock_terraform_service.plan.assert_called_once()
    args, kwargs = mock_terraform_service.plan.call_args
    assert kwargs["module_path"] == TEST_MODULE_PATH
    assert kwargs["variables"] == TEST_VARIABLES


@pytest.mark.asyncio
async def test_run_terraform_apply(mock_db_session, environment_service, mock_terraform_service):
    """Test running terraform apply."""
    # Set up mocks
    mock_env = create_mock_environment()
    mock_env.init_execution_id = "init-12345"
    mock_env.plan_execution_id = "plan-12345"
    environment_service.get_environment = MagicMock(return_value=mock_env)
    environment_service.update_environment_status = MagicMock()
    environment_service.update_environment_execution = MagicMock()
    
    # Mock terraform apply result
    mock_apply_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete! Resources: 2 added, 0 changed, 0 destroyed.",
        duration_ms=300,
        execution_id="apply-12345",
        outputs={"vpc_id": "vpc-12345"}
    )
    mock_terraform_service.apply.return_value = mock_apply_result
    
    # Call the method
    result = await environment_service.run_terraform_apply(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify result
    assert result == mock_apply_result
    
    # Verify method calls
    environment_service.get_environment.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.update_environment_status.assert_called()
    calls = environment_service.update_environment_status.call_args_list
    # First call should be to update status to APPLYING
    first_call = calls[0]
    assert first_call.args[2] == EnvironmentStatus.APPLYING
    # Second call should be to update status to PROVISIONED
    second_call = calls[1]
    assert second_call.args[2] == EnvironmentStatus.PROVISIONED
    
    # Verify terraform service call
    mock_terraform_service.apply.assert_called_once()
    args, kwargs = mock_terraform_service.apply.call_args
    assert kwargs["module_path"] == TEST_MODULE_PATH
    assert kwargs["variables"] == TEST_VARIABLES
    assert kwargs["auto_approve"] is True


@pytest.mark.asyncio
async def test_provision_environment_full_flow(mock_db_session, environment_service):
    """Test the full provisioning flow."""
    # Set up mocks
    mock_env = create_mock_environment()
    environment_service.get_environment = MagicMock(return_value=mock_env)
    
    # Mock the individual terraform operation methods
    init_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Init successful",
        duration_ms=100,
        execution_id="init-12345"
    )
    environment_service.run_terraform_init = AsyncMock(return_value=init_result)
    
    plan_result = TerraformResult(
        operation=TerraformOperation.PLAN,
        success=True,
        output="Plan: 2 to add",
        duration_ms=200,
        execution_id="plan-12345"
    )
    environment_service.run_terraform_plan = AsyncMock(return_value=plan_result)
    
    apply_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete",
        duration_ms=300,
        execution_id="apply-12345"
    )
    environment_service.run_terraform_apply = AsyncMock(return_value=apply_result)
    
    environment_service.update_environment_status = MagicMock()
    
    # Call the method
    await environment_service.provision_environment(mock_db_session, TEST_ENVIRONMENT_ID)
    
    # Verify method calls
    environment_service.get_environment.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.run_terraform_init.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.run_terraform_plan.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)
    environment_service.run_terraform_apply.assert_called_once_with(mock_db_session, TEST_ENVIRONMENT_ID)


def test_get_environment_status(mock_db_session, environment_service):
    """Test getting detailed environment status."""
    # Set up mocks
    mock_env = create_mock_environment(EnvironmentStatus.PROVISIONED.value)
    mock_env.init_execution_id = "init-12345"
    mock_env.plan_execution_id = "plan-12345"
    mock_env.apply_execution_id = "apply-12345"
    environment_service.get_environment = MagicMock(return_value=mock_env)
    
    # Mock os.path.exists and open for state file reading
    mock_state_file_path = f"/tmp/{TEST_MODULE_PATH}/terraform.{TEST_ENVIRONMENT_ID}.tfstate"
    mock_state_data = {
        "resources": [
            {"name": "vpc", "type": "aws_vpc"},
            {"name": "subnet", "type": "aws_subnet"}
        ],
        "outputs": {
            "vpc_id": {"value": "vpc-12345"},
            "subnet_ids": {"value": ["subnet-1", "subnet-2"]}
        }
    }
    
    # Call the method with mocked file operations
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()), \
         patch("json.load", return_value=mock_state_data):
        result = environment_service.get_environment_status(
            mock_db_session, TEST_ENVIRONMENT_ID, correlation_id="test-correlation-id"
        )
    
    # Verify result
    assert result["id"] == TEST_ENVIRONMENT_ID
    assert result["name"] == TEST_ENVIRONMENT_NAME
    assert result["status"] == EnvironmentStatus.PROVISIONED.value
    assert result["init_execution_id"] == "init-12345"
    assert result["plan_execution_id"] == "plan-12345"
    assert result["apply_execution_id"] == "apply-12345"
    assert result["resource_count"] == 2
    assert result["state_file"] == f"terraform.{TEST_ENVIRONMENT_ID}.tfstate"
    assert result["outputs"]["vpc_id"] == "vpc-12345"
    assert result["outputs"]["subnet_ids"] == ["subnet-1", "subnet-2"]


def test_get_environment_status_not_found(mock_db_session, environment_service):
    """Test getting status for non-existent environment."""
    # Set up mocks
    environment_service.get_environment = MagicMock(return_value=None)
    
    # Call the method and check for exception
    with pytest.raises(NotFoundError):
        environment_service.get_environment_status(
            mock_db_session, TEST_ENVIRONMENT_ID, correlation_id="test-correlation-id"
        ) 