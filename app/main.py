from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
from typing import List

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
from app.config import settings, get_settings

# Import database initialization
from app.db.init_db import init_db, run_migrations

# Import logging and exceptions
from app.logging.context import get_logger
from app.logging.middleware import setup_logging_middleware
from app.exceptions import (
    AppException,
    register_exception_handlers
)

# Import routers
from app.routers import terraform, environments, terraform_templates, auth

# Import state module for app-wide state
import app.state

# Import additional exceptions to handle in startup
from app.exceptions.database import MigrationError, DatabaseError
from app.exceptions.operational import ConfigurationError
from app.exceptions.utils import error_context, capture_exception

# Configure structured logger
logger = get_logger("main", metadata={"component": "main"})

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Uses the property that parses CORS_ALLOW_ORIGINS
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,  # Uses the property that parses CORS_ALLOW_METHODS
    allow_headers=settings.CORS_HEADERS,  # Uses the property that parses CORS_ALLOW_HEADERS
)

# Initialize middleware
setup_logging_middleware(app, exclude_paths=["/api/v1/health"])

# Register exception handlers using the new utility function
register_exception_handlers(app)

# Create API router with version prefix
api_router = APIRouter(prefix="/api/v1")


# Health check endpoint
@api_router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check(request: Request, settings=Depends(get_settings)):
    """
    Health check endpoint for the API.
    Used by deployment workflows to verify deployment status.

    Returns:
        Dict: Health status information
    """
    # Log health check
    logger.info(
        "Health check",
        metadata={
            "path": request.url.path,
            "method": request.method
        }
    )

    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root API endpoint
@api_router.get("/", tags=["Root"])
async def api_root(request: Request, settings=Depends(get_settings)):
    """
    Root endpoint for the API.

    Returns:
        Dict: API information
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)

    # Log root access
    logger.info(
        "API root accessed",
        metadata={
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id
        }
    )

    return {
        "message": f"Welcome to the {settings.API_TITLE}",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include the API router
app.include_router(api_router)

# Include other routers
app.include_router(terraform.router)
app.include_router(environments.router)
app.include_router(terraform_templates.router)
app.include_router(auth.router, prefix="/api/v1")

# Initialize Terraform module templates
from app.core.terraform_templates import TemplateManager

template_manager = TemplateManager(settings.TERRAFORM_DIR)

# Make template manager available in app state
@app.on_event("startup")
async def startup_template_manager():
    # Set in app.state for direct access from app instance
    app.state.template_manager = template_manager
    
    # Also set in the state module for import-based access
    app.state.template_manager = template_manager
    
    logger.info("Terraform template manager initialized")

# Root endpoint (outside of API versioning)
@app.get("/", tags=["Root"])
async def root(request: Request, settings=Depends(get_settings)):
    """
    Root endpoint for the application.

    Returns:
        Dict: Application information
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)

    # Log root access
    logger.info(
        "Root accessed",
        metadata={
            "path": request.url.path,
            "method": request.method,
            "correlation_id": correlation_id
        }
    )

    return {
        "message": f"Welcome to the {settings.API_TITLE}",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api": "/api/v1",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Execute tasks on application startup
    """
    logger.info(
        f"Starting {settings.API_TITLE} in {settings.ENVIRONMENT} mode",
        metadata={
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )

    # Get database connection info for logging
    db_url = settings.DATABASE_URL or "sqlite:///./app.db"
    safe_db_url = db_url
    if "@" in safe_db_url:
        # Redact password for logging
        parts = safe_db_url.split('@')
        credentials = parts[0].split("://")[1].split(":")
        if len(credentials) > 1:
            safe_db_url = safe_db_url.replace(f":{credentials[1]}@", ":***@")
    logger.info(f"Using database: {safe_db_url}")

    # Check if tables already exist to log status
    try:
        # Use error_context to add context to any exceptions
        with error_context(operation="startup", component="database"):
            # Import here to avoid circular imports
            from sqlalchemy import inspect
            from app.db.database import engine, schema_name

            inspector = inspect(engine)
            existing_tables = inspector.get_table_names(schema=schema_name)
            tables_exist = len(existing_tables) > 0
            
            if tables_exist:
                logger.info(f"Found existing tables in schema '{schema_name}': {', '.join(existing_tables)}")
            else:
                logger.info(f"No tables found in schema '{schema_name}'. Database needs initialization.")
            
            # Always run migrations on startup
            logger.info("Running database migrations")
            try:
                run_migrations()
            except MigrationError as me:
                logger.error(f"Migration error: {str(me)}", error_id=me.error_id)
                # If no tables exist, fall back to direct creation
                if not tables_exist:
                    logger.info("Falling back to direct table creation")
                    try:
                        init_db()
                    except DatabaseError as de:
                        logger.error(f"Error initializing database: {str(de)}", error_id=de.error_id)
                        # Capture but don't re-raise to allow app to start
                        capture_exception(de, reraise=False, log_level="error")
                # Continue startup even with migration errors
            
    except Exception as e:
        # Use ConfigurationError for unexpected setup issues
        error = ConfigurationError(
            message=f"Error during database setup: {str(e)}",
            parameter="database_setup"
        )
        # Log but don't re-raise to allow app to start even with DB issues
        capture_exception(error, reraise=False, log_level="error")

    logger.info("Application startup completed")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute tasks on application shutdown
    """
    logger.info(
        f"Shutting down {settings.API_TITLE}",
        metadata={
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )


if __name__ == "__main__":
    # Run the application with uvicorn when script is executed directly
    uvicorn.run(
        "app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.API_RELOAD
    )
