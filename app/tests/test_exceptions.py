import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from app.core.exceptions import (
    AppException,
    BadRequestError,
    NotFoundError,
    TerraformError,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


# Create a test app with exception handlers
test_app = FastAPI()
test_app.add_exception_handler(AppException, app_exception_handler)
test_app.add_exception_handler(RequestValidationError, validation_exception_handler)


# Test routes that raise various exceptions
@test_app.get("/test/app-exception")
async def raise_app_exception():
    raise AppException(message="Test app exception")


@test_app.get("/test/bad-request")
async def raise_bad_request():
    raise BadRequestError(message="Test bad request")


@test_app.get("/test/not-found")
async def raise_not_found():
    raise NotFoundError(message="Test not found")


@test_app.get("/test/terraform-error")
async def raise_terraform_error():
    raise TerraformError(message="Test terraform error")


# Model for validation error testing
class TestModel(BaseModel):
    name: str
    age: int = Field(gt=0)


@test_app.post("/test/validation-error")
async def validation_endpoint(data: TestModel):
    return {"received": data.model_dump()}


# Create test client
client = TestClient(test_app)


def test_app_exception():
    """Test that AppException is handled correctly."""
    response = client.get("/test/app-exception")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["message"] == "Test app exception"
    assert "error_id" in data
    assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_bad_request_exception():
    """Test that BadRequestError is handled correctly."""
    response = client.get("/test/bad-request")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["message"] == "Test bad request"
    assert "error_id" in data
    assert data["status_code"] == status.HTTP_400_BAD_REQUEST


def test_not_found_exception():
    """Test that NotFoundError is handled correctly."""
    response = client.get("/test/not-found")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["message"] == "Test not found"
    assert "error_id" in data
    assert data["status_code"] == status.HTTP_404_NOT_FOUND


def test_terraform_exception():
    """Test that TerraformError is handled correctly."""
    response = client.get("/test/terraform-error")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["message"] == "Test terraform error"
    assert "error_id" in data
    assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_validation_exception():
    """Test that validation errors are handled correctly."""
    # Missing required field and invalid value
    test_data = {"age": -1}
    response = client.post("/test/validation-error", json=test_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()

    # Check that the response contains the validation message
    assert "message" in data
    assert "Validation error" in data["message"]
    assert "body.name: Field required" in data["message"]
    assert "body.age: Input should be greater than 0" in data["message"]

    # Verify error structure
    assert "error_id" in data
    assert "status_code" in data
    assert data["status_code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "errors" in data

    # Check that the errors list contains the expected errors
    errors = data["errors"]
    assert len(errors) == 2

    # Check for name error
    name_error = next((e for e in errors if e["loc"] == ["body", "name"]), None)
    assert name_error is not None
    assert name_error["msg"] == "Field required"
    assert name_error["type"] == "missing"

    # Check for age error
    age_error = next((e for e in errors if e["loc"] == ["body", "age"]), None)
    assert age_error is not None
    assert age_error["msg"] == "Input should be greater than 0"
    assert age_error["type"] == "greater_than"


def test_error_details():
    """Test that error details are included in the response."""
    # Create an exception with details
    details = [{"loc": ["field1"], "msg": "Invalid value", "type": "value_error"}]
    exception = BadRequestError(message="Error with details", details=details)

    # Check that attributes are set correctly
    assert exception.message == "Error with details"
    assert exception.status_code == status.HTTP_400_BAD_REQUEST
    assert exception.details == details
    assert exception.error_id is not None
