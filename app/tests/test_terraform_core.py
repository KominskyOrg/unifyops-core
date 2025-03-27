import os
import json
import pytest
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.terraform import (
    TerraformOperation,
    TerraformResult,
    TerraformService,
    run_terraform_command,
)
from app.core.exceptions import TerraformError


@pytest.fixture
def terraform_dir():
    """Create a temporary directory for Terraform files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock Terraform module
        module_dir = os.path.join(tmpdir, "test-module")
        os.makedirs(module_dir)
        # Create an empty main.tf file
        with open(os.path.join(module_dir, "main.tf"), "w") as f:
            f.write("# Test Terraform module\n")

        yield tmpdir


@pytest.mark.asyncio
@patch("app.core.terraform.asyncio.create_subprocess_exec")
async def test_run_terraform_command_success(mock_subprocess):
    """Test successful Terraform command execution."""
    # Mock process
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"Terraform output", b"")
    mock_subprocess.return_value = mock_process

    # Run init
    result = await run_terraform_command(
        operation=TerraformOperation.INIT, working_dir="/tmp", execution_id="test-id"
    )

    # Verify result
    assert result.success is True
    assert result.operation == TerraformOperation.INIT
    assert result.output == "Terraform output"
    assert result.execution_id == "test-id"

    # Verify process was called correctly
    mock_subprocess.assert_called_once()
    # Verify terraform command was invoked correctly
    args, kwargs = mock_subprocess.call_args
    assert args[0] == "terraform"
    assert args[1] == "init"
    assert "-input=false" in args
    assert "-no-color" in args


@pytest.mark.asyncio
@patch("app.core.terraform.asyncio.create_subprocess_exec")
async def test_run_terraform_command_failure(mock_subprocess):
    """Test failed Terraform command execution."""
    # Mock process
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Error message")
    mock_subprocess.return_value = mock_process

    # Run plan
    result = await run_terraform_command(
        operation=TerraformOperation.PLAN, working_dir="/tmp", execution_id="test-id"
    )

    # Verify result
    assert result.success is False
    assert result.operation == TerraformOperation.PLAN
    assert result.error == "Error message"
    assert result.execution_id == "test-id"


@pytest.mark.asyncio
@patch("app.core.terraform.asyncio.create_subprocess_exec")
async def test_run_terraform_command_timeout(mock_subprocess):
    """Test Terraform command timeout."""
    # Mock process
    mock_process = AsyncMock()
    mock_subprocess.return_value = mock_process

    # Make communicate raise TimeoutError
    mock_process.communicate.side_effect = TimeoutError()

    # Run apply with a very short timeout
    result = await run_terraform_command(
        operation=TerraformOperation.APPLY, working_dir="/tmp", timeout=0.1, execution_id="test-id"
    )

    # Verify result
    assert result.success is False
    assert result.operation == TerraformOperation.APPLY
    assert "timed out" in result.error.lower()
    assert result.execution_id == "test-id"


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_init(mock_run_command, terraform_dir):
    """Test TerraformService init method."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function
    mock_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized",
        duration_ms=100,
        execution_id="test-id",
    )
    mock_run_command.return_value = mock_result

    # Test the init method
    result = await service.init(module_path="test-module", backend_config={"bucket": "test-bucket"})

    # Verify result
    assert result == mock_result

    # Verify command was called correctly
    mock_run_command.assert_called_once()
    # Verify working directory and other args were passed correctly
    args, kwargs = mock_run_command.call_args
    assert kwargs["operation"] == TerraformOperation.INIT
    assert kwargs["working_dir"] == os.path.join(terraform_dir, "test-module")
    assert len(kwargs["var_files"]) == 1  # backend config file


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_plan(mock_run_command, terraform_dir):
    """Test TerraformService plan method."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function
    mock_result = TerraformResult(
        operation=TerraformOperation.PLAN,
        success=True,
        output="Plan: 1 to add",
        duration_ms=200,
        execution_id="test-id",
        plan_id="test-plan-id",
    )
    mock_run_command.return_value = mock_result

    # Test the plan method
    variables = {"instance_type": "t2.micro"}
    result = await service.plan(module_path="test-module", variables=variables)

    # Verify result
    assert result == mock_result

    # Verify command was called correctly
    mock_run_command.assert_called_once()
    # Verify working directory and other args were passed correctly
    args, kwargs = mock_run_command.call_args
    assert kwargs["operation"] == TerraformOperation.PLAN
    assert kwargs["working_dir"] == os.path.join(terraform_dir, "test-module")
    assert kwargs["variables"] == variables


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_apply(mock_run_command, terraform_dir):
    """Test TerraformService apply method."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function
    mock_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete",
        duration_ms=300,
        execution_id="test-id",
    )
    mock_run_command.return_value = mock_result

    # Test the apply method
    variables = {"instance_type": "t2.micro"}
    result = await service.apply(module_path="test-module", variables=variables, auto_approve=True)

    # Verify result
    assert result == mock_result

    # Verify command was called correctly
    mock_run_command.assert_called_once()
    # Verify working directory and other args were passed correctly
    args, kwargs = mock_run_command.call_args
    assert kwargs["operation"] == TerraformOperation.APPLY
    assert kwargs["working_dir"] == os.path.join(terraform_dir, "test-module")
    assert kwargs["variables"] == variables
    assert kwargs["auto_approve"] is True


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_apply_with_plan(mock_run_command, terraform_dir):
    """Test TerraformService apply method with a plan ID."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Set up the mocked subprocess for apply with plan
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"Apply complete", b"")

    # Patch the asyncio.create_subprocess_exec in the TerraformService
    with patch("app.core.terraform.asyncio.create_subprocess_exec", return_value=mock_process):
        # Test the apply method with a plan ID
        result = await service.apply(module_path="test-module", plan_id="test-plan-id")

        # Verify result
        assert result.success is True
        assert result.operation == TerraformOperation.APPLY
        assert result.plan_id == "test-plan-id"

        # Verify run_terraform_command was not called
        mock_run_command.assert_not_called()


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_destroy(mock_run_command, terraform_dir):
    """Test TerraformService destroy method."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function
    mock_result = TerraformResult(
        operation=TerraformOperation.DESTROY,
        success=True,
        output="Destroy complete",
        duration_ms=400,
        execution_id="test-id",
    )
    mock_run_command.return_value = mock_result

    # Test the destroy method
    variables = {"instance_type": "t2.micro"}
    result = await service.destroy(
        module_path="test-module", variables=variables, auto_approve=True
    )

    # Verify result
    assert result == mock_result

    # Verify command was called correctly
    mock_run_command.assert_called_once()
    # Verify working directory and other args were passed correctly
    args, kwargs = mock_run_command.call_args
    assert kwargs["operation"] == TerraformOperation.DESTROY
    assert kwargs["working_dir"] == os.path.join(terraform_dir, "test-module")
    assert kwargs["variables"] == variables
    assert kwargs["auto_approve"] is True


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_output(mock_run_command, terraform_dir):
    """Test TerraformService output method."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function with outputs
    mock_outputs = {"instance_id": {"value": "i-12345678"}, "public_ip": {"value": "1.2.3.4"}}
    mock_result = TerraformResult(
        operation=TerraformOperation.OUTPUT,
        success=True,
        output=json.dumps(mock_outputs),
        duration_ms=50,
        execution_id="test-id",
        outputs=mock_outputs,
    )
    mock_run_command.return_value = mock_result

    # Test the output method
    outputs = await service.output(module_path="test-module")

    # Verify outputs match
    assert outputs == mock_outputs

    # Verify command was called correctly
    mock_run_command.assert_called_once()
    args, kwargs = mock_run_command.call_args
    assert kwargs["operation"] == TerraformOperation.OUTPUT
    assert kwargs["working_dir"] == os.path.join(terraform_dir, "test-module")


@pytest.mark.asyncio
@patch("app.core.terraform.run_terraform_command")
async def test_terraform_service_output_failure(mock_run_command, terraform_dir):
    """Test TerraformService output method when the command fails."""
    # Create a service
    service = TerraformService(terraform_dir)

    # Mock the run_terraform_command function with a failure
    mock_result = TerraformResult(
        operation=TerraformOperation.OUTPUT,
        success=False,
        output="",
        error="Failed to get outputs",
        duration_ms=50,
        execution_id="test-id",
    )
    mock_run_command.return_value = mock_result

    # Test the output method - it should raise an exception
    with pytest.raises(TerraformError) as excinfo:
        await service.output(module_path="test-module")

    # Verify the error message
    assert "Failed to get outputs" in str(excinfo.value)
