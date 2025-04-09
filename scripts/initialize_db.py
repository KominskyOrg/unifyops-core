#!/usr/bin/env python3
"""
Database Initialization Script

This script performs complete database initialization:
1. Checks database connectivity
2. Creates the app_schema if it doesn't exist
3. Creates an initial migration if none exists
4. Runs all migrations
5. Initializes SQLAlchemy tables

Usage:
    python scripts/initialize_db.py
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_init")

# Import app modules after path setup
from app.core.config import settings
from app.db.database import SQLALCHEMY_DATABASE_URL, engine, schema_name
from app.models.terraform import Environment  # Import all models
from app.db.database import Base
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

def check_database_connection(max_retries=5, retry_interval=5):
    """Check if database is accessible, with retries"""
    logger.info(f"Checking database connection to {SQLALCHEMY_DATABASE_URL.split('@')[-1]}")
    
    retries = 0
    while retries < max_retries:
        try:
            # Try to connect and run a simple query
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("✅ Database connection successful")
            return True
        except (OperationalError, ProgrammingError) as e:
            retries += 1
            logger.warning(f"Database connection attempt {retries}/{max_retries} failed: {str(e)}")
            if retries < max_retries:
                logger.info(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error("❌ Failed to connect to database after maximum retries")
                return False

def create_schema():
    """Create the application schema if it doesn't exist"""
    try:
        logger.info(f"Creating schema '{schema_name}' if it doesn't exist")
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
        logger.info(f"✅ Schema '{schema_name}' created or already exists")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {str(e)}")
        return False

def get_table_names():
    """Get list of existing tables in database"""
    try:
        inspector = inspect(engine)
        # Look in our specific schema
        return inspector.get_table_names(schema=schema_name)
    except:
        return []

def create_initial_migration():
    """Create the initial migration if none exists"""
    # Get the alembic.ini path
    project_root = Path(__file__).parent.parent
    alembic_ini = project_root / "alembic.ini"
    
    if not alembic_ini.exists():
        logger.error(f"❌ alembic.ini not found at {alembic_ini}")
        return False
    
    # Make sure versions directory exists
    versions_dir = project_root / "alembic" / "versions"
    if not versions_dir.exists():
        logger.info(f"Creating versions directory at {versions_dir}")
        versions_dir.mkdir(exist_ok=True)
    
    # Check if migrations already exist
    if any(versions_dir.iterdir()):
        logger.info("Migration files already exist, skipping creation")
        return True
    
    try:
        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))
        
        # Log current configuration
        logger.info(f"Alembic configuration loaded from {alembic_ini}")
        db_url = alembic_cfg.get_main_option("sqlalchemy.url")
        logger.info(f"Using sqlalchemy.url: {db_url if db_url else 'Not set in config'}")
        
        # Override with environment variable if not set
        if not db_url and settings.DATABASE_URL:
            logger.info("Setting sqlalchemy.url from environment variable")
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # Check script location
        script_location = alembic_cfg.get_main_option("script_location")
        logger.info(f"Script location: {script_location}")
        
        # Create initial migration with detailed tracebacks
        logger.info("Creating initial migration (autogenerate)")
        try:
            command.revision(alembic_cfg, "Initial database setup", autogenerate=True)
            logger.info("✅ Initial migration created successfully")
            return True
        except Exception as e:
            import traceback
            logger.error(f"❌ Migration generation error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try to diagnose common issues
            if "No such file or directory" in str(e):
                logger.error("Directory issue detected. Check if all paths exist and are accessible.")
            elif "Cannot find source model" in str(e):
                logger.error("SQLAlchemy model issue. Check your model imports and definitions.")
            elif "Target database is not up to date" in str(e):
                logger.error("Database schema mismatch. The database might have existing tables not managed by Alembic.")
            
            return False
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to create initial migration: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def run_migrations():
    """Run all pending migrations"""
    # Get the alembic.ini path
    project_root = Path(__file__).parent.parent
    alembic_ini = project_root / "alembic.ini"
    
    if not alembic_ini.exists():
        logger.error(f"❌ alembic.ini not found at {alembic_ini}")
        return False
    
    try:
        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))
        
        # Get migration script directory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        # Get current and head revisions
        head_revision = script_dir.get_current_head()
        if head_revision is None:
            logger.info("No migrations found - empty migration directory")
            return True
        
        # Run migrations
        logger.info(f"Running database migrations to head revision {head_revision}")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to run migrations: {str(e)}")
        return False

def initialize_sqlalchemy_tables():
    """Initialize tables directly with SQLAlchemy (fallback)"""
    try:
        logger.info("Creating tables with SQLAlchemy")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ SQLAlchemy tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables with SQLAlchemy: {str(e)}")
        return False

def main():
    """Main entry point for database initialization"""
    logger.info("Starting database initialization")
    
    # Check for direct table creation flag
    force_direct = "--direct" in sys.argv
    if force_direct:
        logger.info("Direct table creation mode enabled (--direct flag)")
    
    # Check environment
    db_url = settings.DATABASE_URL or "sqlite:///./app.db"
    safe_db_url = db_url
    if "@" in safe_db_url:
        # Redact password for logging
        parts = safe_db_url.split('@')
        credentials = parts[0].split("://")[1].split(":")
        if len(credentials) > 1:
            safe_db_url = safe_db_url.replace(f":{credentials[1]}@", ":***@")
    
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database URL: {safe_db_url}")
    logger.info(f"Using schema: {schema_name}")
    
    # Step 1: Check database connection
    if not check_database_connection():
        sys.exit(1)
    
    # Step 2: Create schema
    if not create_schema():
        logger.error(f"Failed to create schema '{schema_name}'. Check your database permissions.")
        sys.exit(1)
    
    # Step 3: Check if tables exist already
    tables = get_table_names()
    logger.info(f"Existing tables in '{schema_name}': {', '.join(tables) if tables else 'None'}")
    
    # If direct creation is requested, skip migrations
    if force_direct:
        logger.info("Skipping migrations, using direct table creation")
        if not initialize_sqlalchemy_tables():
            logger.error("❌ Database initialization failed completely")
            sys.exit(1)
    else:
        # Step 4: Create initial migration if needed
        if not create_initial_migration():
            logger.warning("Migration creation failed, will try direct table creation")
            if not initialize_sqlalchemy_tables():
                logger.error("❌ Database initialization failed completely")
                sys.exit(1)
        else:
            # Step 5: Run migrations
            migration_success = run_migrations()
            
            # Step 6: Fallback to SQLAlchemy if migrations failed
            if not migration_success:
                logger.warning("Migrations failed, falling back to direct table creation")
                if not initialize_sqlalchemy_tables():
                    logger.error("❌ Database initialization failed completely")
                    sys.exit(1)
    
    # Check if tables were created
    tables_after = get_table_names()
    if tables_after:
        logger.info(f"Final database tables in '{schema_name}': {', '.join(tables_after)}")
        logger.info("✅ Database initialization completed successfully")
    else:
        logger.error(f"❌ No tables found in schema '{schema_name}' after initialization")
        sys.exit(1)

if __name__ == "__main__":
    main() 