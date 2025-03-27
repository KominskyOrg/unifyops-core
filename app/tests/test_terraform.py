import os
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.terraform import TerraformOperation, TerraformResult, TerraformService

client = TestClient(app)

# Since we don't want to actually run Terraform commands during tests,
# we'll need to mock the Terraform functionality


@pytest.fixture
def mock_terraform_service():
    """Fixture to mock the TerraformService."""
    with patch('app.routers.terraform.terraform_service') as mock_service:
        # Ensure that the mocked methods return awaitable objects
        mock_service.init = AsyncMock()
        mock_service.plan = AsyncMock()
        mock_service.apply = AsyncMock()
        mock_service.destroy = AsyncMock()
        mock_service.output = AsyncMock()
        yield mock_service


def test_list_modules():
    """Test listing Terraform modules."""
    response = client.get("/api/v1/terraform/modules")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "modules" in data
    assert isinstance(data["modules"], list)
    
    # Each module should have name, path, and description
    for module in data["modules"]:
        assert "name" in module
        assert "path" in module
        assert "description" in module


@patch('app.routers.terraform.terraform_service.get_terraform_modules')
def test_list_modules_with_mock(mock_get_modules):
    """Test list_modules with a mocked module list."""
    # Set up the mock module data
    mock_module_data = [
        {"name": "vpc", "path": "vpc", "description": "VPC module"},
        {"name": "ec2", "path": "ec2", "description": "EC2 module"}
    ]
    
    # Configure the mock to return our test module data
    mock_get_modules.return_value = mock_module_data

    # Call the endpoint
    response = client.get("/api/v1/terraform/modules")
    assert response.status_code == 200
    data = response.json()

    # Verify the response
    assert data["count"] == 2
    
    # Create sets of tuples for easy comparison regardless of order
    expected_set = {(m["name"], m["path"], m["description"]) for m in mock_module_data}
    actual_set = {(m["name"], m["path"], m["description"]) for m in data["modules"]}
    
    # Verify that the sets match
    assert expected_set == actual_set


def test_init_module_not_found():
    """Test that init module returns 500 for non-existent modules."""
    # Make path.exists return False for non-existent modules
    with patch('os.path.exists', return_value=False):
        # Request data for a non-existent module
        request_data = {
            "module_path": "non-existent-module",
            "variables": {}
        }

        # Call the endpoint
        response = client.post("/api/v1/terraform/init", json=request_data)

        # Print response for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")

        # Check status and error message
        assert response.status_code == 500
        response_json = response.json()
        
        # Check that the response contains the module not found error message
        # The exact key structure depends on the application's error handler implementation
        error_message = str(response_json)
        assert "Module not found" in error_message


@patch('os.path.exists')
def test_init_module_with_mock_terraform_service(mock_exists, mock_terraform_service):
    """Test init module with mocked Terraform service."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the init method to return a successful result
    mock_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="test-execution-id"
    )
    mock_terraform_service.init.return_value = mock_result
    
    # Request data
    request_data = {
        "module_path": "ec2",
        "variables": {},
        "backend_config": {"bucket": "test-bucket"}
    }
    
    # Call the endpoint
    response = client.post("/api/v1/terraform/init", json=request_data)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "init"
    assert data["success"] is True
    assert "initialized successfully" in data["message"]
    assert data["execution_id"] == "test-execution-id"


@patch('os.path.exists')
def test_init_module_force_download(mock_exists, mock_terraform_service):
    """Test init module with force_module_download parameter."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the init method to return a successful result
    mock_result = TerraformResult(
        operation=TerraformOperation.INIT,
        success=True,
        output="Terraform initialized successfully",
        duration_ms=100,
        execution_id="test-execution-id"
    )
    mock_terraform_service.init.return_value = mock_result
    
    # Request data with force_module_download=True
    request_data = {
        "module_path": "ec2",
        "backend_config": {"bucket": "test-bucket"},
        "force_module_download": True
    }
    
    # Call the endpoint
    response = client.post("/api/v1/terraform/init", json=request_data)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "init"
    assert data["success"] is True
    
    # Verify that force_module_download was passed to the service
    mock_terraform_service.init.assert_called_once()
    args, kwargs = mock_terraform_service.init.call_args
    assert kwargs["force_module_download"] is True


@patch('os.path.exists')
def test_plan_module(mock_exists, mock_terraform_service):
    """Test the plan module endpoint."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the plan method to return a successful result
    mock_result = TerraformResult(
        operation=TerraformOperation.PLAN,
        success=True,
        output="Plan: 1 to add, 0 to change, 0 to destroy.",
        duration_ms=200,
        execution_id="test-execution-id",
        plan_id="test-plan-id"
    )
    mock_terraform_service.plan.return_value = mock_result
    
    # Request data
    request_data = {
        "module_path": "ec2",
        "variables": {"instance_type": "t2.micro"}
    }
    
    # Call the endpoint
    response = client.post("/api/v1/terraform/plan", json=request_data)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "plan"
    assert data["success"] is True
    assert data["execution_id"] == "test-execution-id"
    assert data["plan_id"] == "test-plan-id"


@patch('os.path.exists')
def test_apply_module(mock_exists, mock_terraform_service):
    """Test the apply module endpoint."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the apply method to return a successful result
    mock_result = TerraformResult(
        operation=TerraformOperation.APPLY,
        success=True,
        output="Apply complete! Resources: 1 added, 0 changed, 0 destroyed.",
        duration_ms=300,
        execution_id="test-execution-id"
    )
    mock_terraform_service.apply.return_value = mock_result
    
    # Mock the output method to return outputs
    outputs = {
        "instance_id": {"value": "i-12345678"},
        "public_ip": {"value": "1.2.3.4"}
    }
    mock_terraform_service.output.return_value = outputs
    
    # Request data
    request_data = {
        "module_path": "ec2",
        "variables": {"instance_type": "t2.micro"},
        "auto_approve": True
    }
    
    # Call the endpoint
    response = client.post("/api/v1/terraform/apply", json=request_data)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "apply"
    assert data["success"] is True
    assert data["execution_id"] == "test-execution-id"
    assert "outputs" in data
    assert data["outputs"]["instance_id"]["value"] == "i-12345678"


@patch('os.path.exists')
def test_destroy_module(mock_exists, mock_terraform_service):
    """Test the destroy module endpoint."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the destroy method to return a successful result
    mock_result = TerraformResult(
        operation=TerraformOperation.DESTROY,
        success=True,
        output="Destroy complete! Resources: 1 destroyed.",
        duration_ms=300,
        execution_id="test-execution-id"
    )
    mock_terraform_service.destroy.return_value = mock_result
    
    # Request data
    request_data = {
        "module_path": "ec2",
        "variables": {"instance_type": "t2.micro"},
        "auto_approve": True
    }
    
    # Call the endpoint
    response = client.post("/api/v1/terraform/destroy", json=request_data)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["operation"] == "destroy"
    assert data["success"] is True
    assert data["execution_id"] == "test-execution-id"


@patch('os.path.exists')
def test_get_outputs(mock_exists, mock_terraform_service):
    """Test the get outputs endpoint."""
    # Make os.path.exists return True for the module path check
    mock_exists.return_value = True
    
    # Mock the output method to return outputs
    outputs = {
        "instance_id": {"value": "i-12345678"},
        "public_ip": {"value": "1.2.3.4"}
    }
    mock_terraform_service.output.return_value = outputs
    
    # Call the endpoint
    response = client.get("/api/v1/terraform/outputs/ec2")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "ec2"
    assert "outputs" in data
    assert data["outputs"]["instance_id"]["value"] == "i-12345678"
    assert data["outputs"]["public_ip"]["value"] == "1.2.3.4" 