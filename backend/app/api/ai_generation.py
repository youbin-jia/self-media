# backend/app/api/ai_generation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.ai_generation import get_manager

router = APIRouter(prefix="/api/ai-generation", tags=["AI Generation"])


class GenerateImageRequest(BaseModel):
    prompt: str
    provider: str = "dalle"
    style: str = "realistic"
    size: List[int] = [1920, 1080]


class GenerateMusicRequest(BaseModel):
    script_context: dict
    duration: float
    provider: str
    mood: str = "auto"


@router.get("/providers")
async def list_providers():
    """List all available AI generation providers"""
    manager = get_manager()
    return {"providers": manager.list_providers()}


@router.post("/generate-image")
async def generate_image(request: GenerateImageRequest):
    """Generate an image using AI"""
    manager = get_manager()

    try:
        # Convert list to tuple for size
        size_tuple = tuple(request.size) if request.size else (1920, 1080)

        result = await manager.generate_image(
            provider_name=request.provider,
            prompt=request.prompt,
            style=request.style,
            size=size_tuple
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-music")
async def generate_music(request: GenerateMusicRequest):
    """Generate music using AI"""
    manager = get_manager()

    try:
        result = await manager.generate_music(
            provider_name=request.provider,
            script_context=request.script_context,
            duration=request.duration,
            mood=request.mood
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
