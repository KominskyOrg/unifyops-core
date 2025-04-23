import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

# Use our new fixtures for testing
def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "version": "0.1.0",
        "environment": "development" 
    }
