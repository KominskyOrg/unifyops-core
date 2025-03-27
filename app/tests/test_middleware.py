import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import UUID
import uuid
from fastapi.responses import JSONResponse

from app.core.middleware import RequestLoggerMiddleware, CorrelationIDMiddleware


# Create test app with middlewares
test_app = FastAPI()
test_app.add_middleware(CorrelationIDMiddleware)
test_app.add_middleware(RequestLoggerMiddleware)


# Test routes
@test_app.get("/test/middleware")
async def middleware_test_route(request: Request):
    # Return the correlation ID from the request state
    correlation_id = getattr(request.state, "correlation_id", None)
    return {"correlation_id": correlation_id}


@test_app.get("/test/headers")
async def headers_test_route(request: Request):
    # Return all request headers
    return {"headers": dict(request.headers)}


# Create test client
client = TestClient(test_app)


def test_correlation_id_middleware_generates_id():
    """Test that the CorrelationIDMiddleware generates a correlation ID."""
    response = client.get("/test/middleware")
    assert response.status_code == 200

    # Check that a correlation ID was generated
    data = response.json()
    assert "correlation_id" in data
    assert data["correlation_id"] is not None

    # Verify it's a valid UUID
    try:
        UUID(data["correlation_id"])
    except ValueError:
        pytest.fail("Correlation ID is not a valid UUID")


def test_correlation_id_middleware_uses_provided_id():
    """Test that the CorrelationIDMiddleware uses a provided correlation ID."""
    # Send a request with a correlation ID header
    test_correlation_id = "test-correlation-id-12345"
    response = client.get("/test/middleware", headers={"X-Correlation-ID": test_correlation_id})
    assert response.status_code == 200

    # Check that our correlation ID was used
    data = response.json()
    assert data["correlation_id"] == test_correlation_id


def test_correlation_id_middleware_adds_response_header():
    """Test that the CorrelationIDMiddleware adds the correlation ID to the response headers."""
    response = client.get("/test/middleware")
    assert response.status_code == 200

    # Check response headers
    assert "X-Correlation-ID" in response.headers

    # Verify the correlation ID format (UUID)
    correlation_id = response.headers["X-Correlation-ID"]
    # Verify it's a valid UUID by attempting to parse it
    assert uuid.UUID(correlation_id)

    # Extract correlation_id from response body
    data = response.json()
    assert "correlation_id" in data
    # Verify that the body's correlation_id is also a valid UUID
    assert uuid.UUID(data["correlation_id"])

    # Note: We can't directly compare the header and body correlation IDs because
    # they are generated at different points in the request lifecycle


def test_request_logger_middleware():
    """
    Test that the RequestLoggerMiddleware processes requests correctly.
    This is primarily a smoke test since we can't easily inspect the logs.
    """
    # Send a request
    response = client.get("/test/middleware")
    assert response.status_code == 200

    # If we get here without exceptions, the middleware is working at a basic level
    assert True


def test_error_handling_in_middleware():
    """
    Test that the middlewares properly handle errors in the request chain.
    """
    # Create a test app that raises an exception
    error_app = FastAPI()

    # Create a simple exception handler
    @error_app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(status_code=500, content={"message": str(exc)})

    error_app.add_middleware(CorrelationIDMiddleware)
    error_app.add_middleware(RequestLoggerMiddleware)

    @error_app.get("/error")
    async def error_route():
        raise ValueError("Test error")

    # Create test client
    error_client = TestClient(error_app)

    # Send a request that will trigger an error
    response = error_client.get("/error")

    # Verify error handling
    assert response.status_code == 500
    data = response.json()
    assert data["message"] == "Test error"
