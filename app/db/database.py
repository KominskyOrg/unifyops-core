from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# This is a placeholder for future database implementation
# The actual database connection will be set up when needed

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL or "sqlite:///./app.db"

# Create a custom schema-aware metadata
schema_name = "app_schema"
metadata = MetaData(schema=schema_name)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Use our schema-aware metadata for the Base
Base = declarative_base(metadata=metadata)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
