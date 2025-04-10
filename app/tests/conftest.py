import os
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from fastapi.testclient import TestClient
from pathlib import Path
from alembic.config import Config
from alembic import command

from app.main import app
from app.db.database import Base, get_db
from app.models.terraform import *  # Import all models

# Use PostgreSQL test database
TEST_SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "postgresql://postgres:postgres@db:5432/unifyops_test"
)

@pytest.fixture(scope="session")
def test_engine():
    # Create a test database URL
    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@db:5432/test_db")
    
    # First connect to the default postgres database to create our test database
    default_db_url = "postgresql://postgres:postgres@db:5432/postgres"
    default_engine = create_engine(default_db_url)
    
    # Create test database if it doesn't exist
    with default_engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Close any open transaction
        conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'test_db'"))
        if not conn.scalar():
            conn.execute(text("CREATE DATABASE test_db"))
        conn.commit()
    
    # Create test engine
    engine = create_engine(test_db_url)
    
    # Create schema if it doesn't exist
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS app_schema CASCADE"))
        conn.execute(text("CREATE SCHEMA app_schema"))
        conn.commit()
    
    # Get the alembic.ini path and create config
    alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    
    # Set the SQLAlchemy URL in the alembic config
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    
    try:
        # Run the migrations
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Migration failed: {e}")
        # Fallback to direct table creation
        Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Drop all tables and schema after tests
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS app_schema CASCADE"))
        conn.commit()


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