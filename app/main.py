from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
import uvicorn
import os
import sys
import time
from typing import List

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
from app.core.config import settings, get_settings

# Import logging and exceptions
from app.core.logging import get_logger
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_exception_handler,
)
from app.core.middleware import init_middleware

# Import routers
from app.routers import terraform, environment, resource

# Import database initialization
from app.db.init_db import init_db, run_migrations

# Configure structured logger
logger = get_logger("main")

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

# Initialize middleware
init_middleware(app)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, internal_exception_handler)

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
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)

    # Log health check
    logger.info(
        "Health check", path=request.url.path, method=request.method, correlation_id=correlation_id
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
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
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
app.include_router(environment.router)
app.include_router(resource.router)


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
        "Root accessed", path=request.url.path, method=request.method, correlation_id=correlation_id
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
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
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
        migrations_success = run_migrations()
        
        # If migrations failed and no tables exist, fall back to direct creation
        if not migrations_success and not tables_exist:
            logger.info("Falling back to direct table creation")
            try:
                init_db()
            except Exception as init_error:
                logger.error(f"Error initializing database: {str(init_error)}")
    except Exception as e:
        logger.error(f"Error during database setup: {str(e)}")
        # Continue app startup even if database setup fails

    logger.info("Application startup completed")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute tasks on application shutdown
    """
    logger.info(
        f"Shutting down {settings.API_TITLE}",
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
    )


if __name__ == "__main__":
    # Run the application with uvicorn when script is executed directly
    uvicorn.run(
        "app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.API_RELOAD
    )
