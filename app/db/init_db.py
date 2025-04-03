from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import subprocess
import sys
import os

from app.db.database import Base
from app.core.config import settings
from app.core.logging import get_logger

# Import models to include them in SQLAlchemy's metadata
from app.models.environment import Environment

logger = get_logger("db.init")


def init_db():
    """
    Initialize the database by creating all tables
    """
    logger.info("Initializing database")

    # Get database URL from settings
    database_url = settings.DATABASE_URL or "sqlite:///./app.db"

    # Create engine
    if database_url.startswith("sqlite"):
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized")


def run_migrations():
    """
    Run database migrations using alembic
    """
    try:
        logger.info("Running database migrations")
        from alembic.config import Config
        from alembic import command
        
        # Get the alembic.ini path
        alembic_ini = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'alembic.ini')
        
        # Create Alembic config
        alembic_cfg = Config(alembic_ini)
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running database migrations: {str(e)}", exception=e)
        raise


if __name__ == "__main__":
    init_db()
