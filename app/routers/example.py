from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.core.config import get_settings, Settings

# Create router with tags for documentation
router = APIRouter(prefix="/examples", tags=["Examples"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_examples(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Get a list of examples.
    This endpoint demonstrates a basic GET request.
    """
    # This is a dummy implementation - in a real app, you would fetch from a database
    examples = [
        {"id": 1, "name": "Example 1", "description": "This is the first example"},
        {"id": 2, "name": "Example 2", "description": "This is the second example"},
    ]

    return {"examples": examples, "count": len(examples), "environment": settings.ENVIRONMENT}


@router.get("/{example_id}", status_code=status.HTTP_200_OK)
async def get_example(
    example_id: int, settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get a specific example by ID.
    This endpoint demonstrates path parameters.
    """
    # This is a dummy implementation - in a real app, you would fetch from a database
    examples = {
        1: {"id": 1, "name": "Example 1", "description": "This is the first example"},
        2: {"id": 2, "name": "Example 2", "description": "This is the second example"},
    }

    if example_id not in examples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Example with ID {example_id} not found"
        )

    return examples[example_id]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_example(
    example: Dict[str, Any], settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Create a new example.
    This endpoint demonstrates a POST request.
    """
    # This is a dummy implementation - in a real app, you would save to a database
    return {
        "id": 3,  # In a real app, this would be generated
        "name": example.get("name", "New Example"),
        "description": example.get("description", ""),
        "created": True,
        "environment": settings.ENVIRONMENT,
    }
