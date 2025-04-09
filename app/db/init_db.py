from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import subprocess
import sys
import os

from app.db.database import Base
from app.core.config import settings
from app.core.logging import get_logger

# Import models to include them in SQLAlchemy's metadata
from app.models.terraform import Environment

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
    Run database migrations using alembic in a subprocess with timeout
    to prevent hanging
    """
    try:
        logger.info("Running database migrations")
        import subprocess
        import threading
        import time
        
        # Use a subprocess to run alembic, which can be killed if it hangs
        migration_process = subprocess.Popen(
            ["alembic", "upgrade", "head"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Set a timeout (15 seconds)
        timeout = 15
        start_time = time.time()
        
        # Poll the process until it finishes or times out
        while migration_process.poll() is None:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Migration timed out after {timeout} seconds")
                # Force kill the process
                migration_process.kill()
                return False
            # Sleep briefly to avoid busy-waiting
            time.sleep(0.1)
        
        # Get return code
        return_code = migration_process.returncode
        
        # Read output
        stdout, stderr = migration_process.communicate()
        
        if return_code != 0:
            logger.error(f"Migration failed with return code {return_code}")
            if stderr:
                logger.error(f"Migration error: {stderr}")
            raise Exception(f"Migration failed: {stderr}")
        
        logger.info("Database migrations completed successfully")
        return True
            
    except Exception as e:
        logger.error(f"Error running database migrations: {str(e)}")
        return False


if __name__ == "__main__":
    init_db()
