from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import routers
# from app.routers import example_router

# Create FastAPI app
app = FastAPI(
    title="UnifyOps Backend API",
    description="API for the UnifyOps platform",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with version prefix
api_router = APIRouter(prefix="/api/v1")

# Health check endpoint
@api_router.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """
    Health check endpoint for the API.
    Used by deployment workflows to verify deployment status.
    """
    return {
        "status": "healthy",
        "version": app.version
    }

# Root API endpoint
@api_router.get("/", tags=["Root"])
async def api_root():
    """
    Root endpoint for the API.
    """
    return {
        "message": "Welcome to the UnifyOps Backend API",
        "version": app.version
    }

# Include the API router
app.include_router(api_router)

# Root endpoint (outside of API versioning)
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint for the application.
    """
    return {
        "message": "Welcome to the UnifyOps Backend API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api": "/api/v1"
    }

# Include other routers
# app.include_router(example_router.router, prefix="/api/v1")

if __name__ == "__main__":
    # Run the application with uvicorn when script is executed directly
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)