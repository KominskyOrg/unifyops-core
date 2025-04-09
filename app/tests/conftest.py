import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db

# Use PostgreSQL test database
TEST_SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "postgresql://postgres:postgres@db:5432/unifyops_test"
)

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)
    
    # Tables are created by Alembic migrations in the Makefile
    
    yield engine
    
    # We don't drop tables here as they will be dropped when the database is dropped


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with the test database session."""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = _get_test_db
    
    with TestClient(app) as client:
        yield client
    
    # Clean up the dependency override
    app.dependency_overrides = {} 