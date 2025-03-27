from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


if __name__ == "__main__":
    init_db()
