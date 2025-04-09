#!/usr/bin/env python3
"""
Database Schema Permissions Setup

This script sets up proper permissions for the app_schema for the current database user.
It should be run by a database admin user with sufficient privileges.

Usage:
    python scripts/setup_db_permissions.py

Requirements:
    - psycopg2-binary
    - The script must be run by a user with admin privileges
"""

import os
import sys
import logging
import getpass
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_permissions")

try:
    import psycopg2
    from psycopg2 import sql
    from app.db.database import schema_name
    from app.core.config import settings
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    logger.error("Make sure psycopg2-binary is installed: pip install psycopg2-binary")
    sys.exit(1)

def get_db_params():
    """Get database connection parameters"""
    db_url = settings.DATABASE_URL
    
    if not db_url:
        logger.error("DATABASE_URL is not set in environment variables")
        sys.exit(1)
        
    # Parse the database URL
    # Format: postgresql://username:password@host:port/dbname
    parts = db_url.split("://")[1].split("@")
    credentials = parts[0].split(":")
    host_port_db = parts[1].split("/")
    
    username = credentials[0]
    password = credentials[1] if len(credentials) > 1 else ""
    
    host_port = host_port_db[0].split(":")
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    
    dbname = host_port_db[1] if len(host_port_db) > 1 else "postgres"
    
    # Ask for admin credentials
    admin_user = input(f"Enter database admin username (default: postgres): ") or "postgres"
    admin_password = getpass.getpass(f"Enter password for {admin_user}: ")
    
    return {
        "app_user": username,
        "dbname": dbname,
        "host": host,
        "port": port,
        "admin_user": admin_user,
        "admin_password": admin_password
    }

def setup_schema_permissions(params):
    """Set up schema permissions for the application user"""
    try:
        logger.info(f"Connecting to database {params['dbname']} as {params['admin_user']}")
        conn = psycopg2.connect(
            dbname=params['dbname'],
            user=params['admin_user'],
            password=params['admin_password'],
            host=params['host'],
            port=params['port']
        )
        
        # Auto-commit mode
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create schema if it doesn't exist
        logger.info(f"Creating schema '{schema_name}' if it doesn't exist")
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name))
        )
        
        # Grant usage on schema to app user
        logger.info(f"Granting USAGE on schema '{schema_name}' to {params['app_user']}")
        cursor.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(schema_name),
                sql.Identifier(params['app_user'])
            )
        )
        
        # Grant all privileges on all tables in schema to app user
        logger.info(f"Granting ALL PRIVILEGES on all tables in schema '{schema_name}' to {params['app_user']}")
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema_name),
                sql.Identifier(params['app_user'])
            )
        )
        
        # Grant all privileges on all sequences in schema to app user
        logger.info(f"Granting ALL PRIVILEGES on all sequences in schema '{schema_name}' to {params['app_user']}")
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                sql.Identifier(schema_name),
                sql.Identifier(params['app_user'])
            )
        )
        
        # Set default privileges for future tables
        logger.info(f"Setting default privileges for future tables in schema '{schema_name}'")
        cursor.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT ALL PRIVILEGES ON TABLES TO {}").format(
                sql.Identifier(schema_name),
                sql.Identifier(params['app_user'])
            )
        )
        
        # Set default privileges for future sequences
        logger.info(f"Setting default privileges for future sequences in schema '{schema_name}'")
        cursor.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT ALL PRIVILEGES ON SEQUENCES TO {}").format(
                sql.Identifier(schema_name),
                sql.Identifier(params['app_user'])
            )
        )
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Successfully set up permissions for schema '{schema_name}'")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set up schema permissions: {str(e)}")
        return False

def main():
    """Main entry point for database permission setup"""
    logger.info("Starting database permission setup")
    
    # Get database parameters
    params = get_db_params()
    
    # Set up schema permissions
    success = setup_schema_permissions(params)
    
    if success:
        logger.info("✅ Database permission setup completed successfully")
    else:
        logger.error("❌ Database permission setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 