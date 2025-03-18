from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_examples():
    """Test that the examples endpoint returns a list of examples."""
    response = client.get("/api/v1/examples/")
    assert response.status_code == 200
    data = response.json()
    assert "examples" in data
    assert isinstance(data["examples"], list)
    assert len(data["examples"]) > 0
    assert data["count"] == len(data["examples"])


def test_get_example():
    """Test that the example endpoint returns a specific example."""
    response = client.get("/api/v1/examples/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "name" in data
    assert "description" in data


def test_get_example_not_found():
    """Test that the example endpoint returns 404 for non-existent examples."""
    response = client.get("/api/v1/examples/999")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_create_example():
    """Test that the create example endpoint returns the created example."""
    test_data = {"name": "Test Example", "description": "This is a test example"}
    response = client.post("/api/v1/examples/", json=test_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == test_data["name"]
    assert data["description"] == test_data["description"]
    assert data["created"] is True 