from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
import logging
from typing import List

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
from app.core.config import settings, get_settings

# Import routers
from app.routers import example

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with version prefix
api_router = APIRouter(prefix="/api/v1")

# Health check endpoint
@api_router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check(settings=Depends(get_settings)):
    """
    Health check endpoint for the API.
    Used by deployment workflows to verify deployment status.
    """
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Root API endpoint
@api_router.get("/", tags=["Root"])
async def api_root(settings=Depends(get_settings)):
    """
    Root endpoint for the API.
    """
    return {
        "message": f"Welcome to the {settings.API_TITLE}",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Include the API router
app.include_router(api_router)

# Include other routers
app.include_router(example.router, prefix="/api/v1")

# Root endpoint (outside of API versioning)
@app.get("/", tags=["Root"])
async def root(settings=Depends(get_settings)):
    """
    Root endpoint for the application.
    """
    return {
        "message": f"Welcome to the {settings.API_TITLE}",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api": "/api/v1",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    # Run the application with uvicorn when script is executed directly
    logger.info(f"Starting {settings.API_TITLE} in {settings.ENVIRONMENT} mode")
    uvicorn.run(
        "app.main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT, 
        reload=settings.API_RELOAD
    )