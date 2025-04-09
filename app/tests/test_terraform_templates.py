import os
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.terraform_templates import TemplateManager, ModuleTemplate, AWSS3BucketTemplate
import app.state

# Create a test client that will be used by all tests
client = TestClient(app)

# Setup the app.state.template_manager before tests run
@pytest.fixture(autouse=True)
def setup_app_state():
    """
    Initialize app state for all tests to ensure the template_manager is available.
    This fixture runs automatically for all tests in this module.
    """
    # Create a mock template manager
    mock_tm = MagicMock(spec=TemplateManager)
    # Set it in the app state
    app.state.template_manager = mock_tm
    # Set it in the app.state module (for import-based access)
    app.state.template_manager = mock_tm
    yield
    # Cleanup after tests
    if hasattr(app.state, "template_manager"):
        delattr(app.state, "template_manager")


@pytest.fixture
def mock_template_manager():
    """Fixture to mock the TemplateManager."""
    with patch("app.state.template_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def sample_templates():
    """Return a list of sample templates for testing."""
    return [
        {
            "id": "aws/storage/s3_bucket",
            "name": "s3_bucket",
            "description": "AWS S3 bucket with configurable properties",
            "category": "storage",
            "provider": "aws"
        },
        {
            "id": "aws/compute/lambda_function",
            "name": "lambda_function",
            "description": "AWS Lambda function with IAM role and CloudWatch logging",
            "category": "compute",
            "provider": "aws"
        },
        {
            "id": "azure/storage/storage_account",
            "name": "storage_account",
            "description": "Azure Storage Account with configurable access and encryption",
            "category": "storage",
            "provider": "azure"
        }
    ]


@pytest.fixture
def sample_template_details():
    """Return detailed information about a sample template."""
    return {
        "id": "aws/storage/s3_bucket",
        "name": "s3_bucket",
        "description": "AWS S3 bucket with configurable properties",
        "category": "storage",
        "provider": "aws",
        "variables": [
            {
                "name": "bucket_name",
                "description": "Name of the S3 bucket",
                "type": "string",
                "required": True
            },
            {
                "name": "enable_versioning",
                "description": "Enable versioning for the bucket",
                "type": "bool",
                "default": "true",
                "required": False
            }
        ],
        "outputs": [
            {
                "name": "bucket_id",
                "description": "The ID of the S3 bucket"
            },
            {
                "name": "bucket_arn",
                "description": "The ARN of the S3 bucket"
            }
        ]
    }


def test_list_templates(mock_template_manager, sample_templates):
    """Test listing available templates."""
    # Configure the mock to return our sample templates
    mock_template_manager.get_available_templates.return_value = sample_templates
    
    # Call the endpoint
    response = client.get("/terraform/templates/")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == "aws/storage/s3_bucket"
    assert data[1]["id"] == "aws/compute/lambda_function"
    assert data[2]["id"] == "azure/storage/storage_account"
    
    # Verify template manager was called correctly
    mock_template_manager.get_available_templates.assert_called_once()


def test_list_templates_with_filter(mock_template_manager, sample_templates):
    """Test listing templates with filtering."""
    # Configure the mock to return our sample templates
    mock_template_manager.get_available_templates.return_value = sample_templates
    
    # Call the endpoint with provider filter
    response = client.get("/terraform/templates/?provider=aws")
    
    # We're not mocking the filtering logic, as it's handled by the route function
    # Just test that the endpoint is callable and doesn't raise errors
    assert response.status_code == 200
    
    # Verify template manager was called correctly
    mock_template_manager.get_available_templates.assert_called_once()


def test_get_template_details(mock_template_manager, sample_template_details):
    """Test getting detailed information about a template."""
    # Configure the mock to return our sample template details
    mock_template_manager.get_template_details.return_value = sample_template_details
    
    # Call the endpoint
    response = client.get("/terraform/templates/aws/storage/s3_bucket")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "aws/storage/s3_bucket"
    assert data["name"] == "s3_bucket"
    assert len(data["variables"]) == 2
    assert len(data["outputs"]) == 2
    
    # Verify template manager was called correctly
    mock_template_manager.get_template_details.assert_called_once_with("aws/storage/s3_bucket")


def test_get_template_details_not_found(mock_template_manager):
    """Test handling of template not found."""
    # Configure the mock to raise ValueError
    mock_template_manager.get_template_details.side_effect = ValueError("Template not found")
    
    # Call the endpoint
    response = client.get("/terraform/templates/nonexistent")
    
    # Check response
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
    
    # Verify template manager was called correctly
    mock_template_manager.get_template_details.assert_called_once_with("nonexistent")


def test_create_module_from_template(mock_template_manager):
    """Test creating a module from a template."""
    # Configure the mock
    mock_template_manager.create_module_from_template.return_value = "custom/aws/s3_bucket"
    
    # Request data
    request_data = {
        "template_id": "aws/storage/s3_bucket",
        "target_path": "custom/aws/s3_bucket",
        "variables": {
            "bucket_name": "my-unique-bucket"
        }
    }
    
    # Call the endpoint
    response = client.post("/terraform/templates/create-module", json=request_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["module_path"] == "custom/aws/s3_bucket"
    assert data["template_id"] == "aws/storage/s3_bucket"
    
    # Verify template manager was called correctly
    mock_template_manager.create_module_from_template.assert_called_once_with(
        template_id="aws/storage/s3_bucket",
        target_path="custom/aws/s3_bucket",
        variables={"bucket_name": "my-unique-bucket"}
    )


def test_create_module_from_template_error(mock_template_manager):
    """Test handling of errors when creating a module from a template."""
    # Configure the mock to raise ValueError
    error_message = "Target directory already exists"
    mock_template_manager.create_module_from_template.side_effect = ValueError(error_message)
    
    # Request data
    request_data = {
        "template_id": "aws/storage/s3_bucket",
        "target_path": "existing/path",
        "variables": {}
    }
    
    # Call the endpoint
    response = client.post("/terraform/templates/create-module", json=request_data)
    
    # Check response
    assert response.status_code == 400
    data = response.json()
    assert error_message in data["detail"]
    
    # Verify template manager was called correctly
    mock_template_manager.create_module_from_template.assert_called_once()


# Unit tests for the TemplateManager class
def test_template_manager_get_available_templates():
    """Test TemplateManager.get_available_templates()."""
    # Create a TemplateManager with a test directory
    manager = TemplateManager("/tmp/test")
    
    # The method should return templates from the self.templates dict
    templates = manager.get_available_templates()
    
    # Verify that the templates list is not empty and has the expected format
    assert len(templates) > 0
    for template in templates:
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "category" in template
        assert "provider" in template


def test_template_manager_get_template_details():
    """Test TemplateManager.get_template_details()."""
    # Create a TemplateManager with a test directory
    manager = TemplateManager("/tmp/test")
    
    # Get details for a known template (AWS S3 bucket)
    template_id = "aws/storage/s3_bucket"
    details = manager.get_template_details(template_id)
    
    # Verify the details
    assert details["id"] == template_id
    assert details["name"] == "s3_bucket"
    assert "variables" in details
    assert "outputs" in details
    
    # Verify that variables and outputs are lists
    assert isinstance(details["variables"], list)
    assert isinstance(details["outputs"], list)
    
    # Check for required fields in variables
    for variable in details["variables"]:
        assert "name" in variable
        assert "description" in variable
        assert "type" in variable
        assert "required" in variable
    
    # Check for required fields in outputs
    for output in details["outputs"]:
        assert "name" in output
        assert "description" in output


def test_template_manager_get_template_details_not_found():
    """Test TemplateManager.get_template_details() with nonexistent template."""
    # Create a TemplateManager with a test directory
    manager = TemplateManager("/tmp/test")
    
    # Try to get details for a nonexistent template
    with pytest.raises(ValueError) as excinfo:
        manager.get_template_details("nonexistent/template")
    
    # Verify the error message
    assert "not found" in str(excinfo.value).lower()


# Tests for the template module creation
@patch("os.makedirs")
@patch("os.path.exists")
@patch("builtins.open", new_callable=MagicMock)
def test_create_module_from_template(mock_open, mock_exists, mock_makedirs):
    """Test creating a module from a template."""
    # Configure mocks
    mock_exists.return_value = False  # Target directory doesn't exist
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Create a TemplateManager with a test directory
    manager = TemplateManager("/tmp/test_tf")
    
    # Create a module from a template
    template_id = "aws/storage/s3_bucket"
    target_path = "custom/s3_bucket"
    variables = {"bucket_name": "my-test-bucket"}
    
    result = manager.create_module_from_template(template_id, target_path, variables)
    
    # Verify the result
    assert result == target_path
    
    # Verify directory creation
    mock_makedirs.assert_called_once_with(os.path.join("/tmp/test_tf", target_path), exist_ok=True)
    
    # Verify file creation (should be called multiple times, once for each file)
    assert mock_open.call_count > 0


@patch("os.path.exists")
def test_create_module_existing_directory(mock_exists):
    """Test error handling when target directory already exists."""
    # Configure mocks
    mock_exists.return_value = True  # Target directory already exists
    
    # Create a TemplateManager with a test directory
    manager = TemplateManager("/tmp/test_tf")
    
    # Try to create a module in an existing directory
    template_id = "aws/storage/s3_bucket"
    target_path = "existing/path"
    
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        manager.create_module_from_template(template_id, target_path)
    
    # Verify the error message
    assert "already exists" in str(excinfo.value).lower() 