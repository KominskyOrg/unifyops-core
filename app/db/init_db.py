from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import subprocess
import sys
import os
import time

from app.db.database import Base
from app.config import settings
from app.logging.context import get_logger

# Import models to include them in SQLAlchemy's metadata
from app.models.terraform import Environment

# Import exceptions from the new package
from app.exceptions.database import MigrationError, DatabaseError
from app.exceptions.utils import error_context

logger = get_logger("db.init", metadata={"component": "db.init"})


def init_db():
    """
    Initialize the database by creating all tables
    """
    logger.info("Initializing database")

    # Use error_context to add context to any exceptions
    with error_context(operation="init_db"):
        try:
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
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            # Use DatabaseError from our new exceptions package
            raise DatabaseError(message=f"Database initialization failed: {str(e)}", operation="init_db")


def run_migrations():
    """
    Run database migrations using alembic in a subprocess with timeout
    to prevent hanging
    """
    migration_process = None
    
    try:
        logger.info("Running database migrations")
        
        # Use error_context to add context to any exceptions
        with error_context(operation="run_migrations"):
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
                    # Use MigrationError from our new exceptions package
                    raise MigrationError(
                        message=f"Database migration timed out after {timeout} seconds",
                        migration_direction="upgrade",
                    )
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
                # Use MigrationError from our new exceptions package
                raise MigrationError(
                    message=f"Migration failed: {stderr}",
                    migration_direction="upgrade",
                    details=[{
                        "return_code": return_code,
                        "stderr": stderr
                    }]
                )
            
            logger.info("Database migrations completed successfully")
            return True
                
    except MigrationError:
        # Re-raise MigrationError exceptions
        raise
    except Exception as e:
        logger.error(f"Error running database migrations: {str(e)}")
        # Use MigrationError from our new exceptions package
        raise MigrationError(
            message=f"Error running database migrations: {str(e)}",
            migration_direction="upgrade"
        )
    finally:
        # Make sure to kill the process if it's still running
        if migration_process and migration_process.poll() is None:
            migration_process.kill()


if __name__ == "__main__":
    init_db()
