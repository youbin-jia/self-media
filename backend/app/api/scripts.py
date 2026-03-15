# backend/app/api/scripts.py
"""Script API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.script import Script
from app.models.project import Project
from app.schemas.script import ScriptCreate, ScriptUpdate, ScriptResponse, ScriptSegment
from app.services.script_generator import ScriptGenerator

router = APIRouter()


@router.post("/generate-outline", response_model=dict)
async def generate_outline(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a script outline for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Dictionary with outline text
    """
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate outline
    generator = ScriptGenerator()
    topic = project.topic_title or project.title
    outline = await generator.generate_outline(topic)

    # Create or update script
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        script = Script(
            project_id=project_id,
            outline=outline,
            version=1,
            is_approved=False
        )
        db.add(script)
    else:
        script.outline = outline
        script.version = (script.version or 1) + 1

    db.commit()
    db.refresh(script)

    return {
        "script_id": script.id,
        "outline": outline
    }


@router.post("/generate-full", response_model=ScriptResponse)
async def generate_full_script(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a full script with segments for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        ScriptResponse with full script and segments
    """
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get existing script with outline
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script or not script.outline:
        raise HTTPException(
            status_code=400,
            detail="No outline found. Please generate outline first."
        )

    # Generate full script
    generator = ScriptGenerator()
    topic = project.topic_title or project.title
    result = await generator.generate_full_script(script.outline, topic)

    # Update script
    script.full_script = result["full_script"]
    script.segments = [seg.model_dump() for seg in result["segments"]]
    script.version = (script.version or 1) + 1

    db.commit()
    db.refresh(script)

    return script


@router.post("/{script_id}/approve", response_model=ScriptResponse)
async def approve_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Approve a script

    Args:
        script_id: The script ID
        db: Database session

    Returns:
        Updated ScriptResponse
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script.is_approved = True
    db.commit()
    db.refresh(script)

    return script


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a script by ID

    Args:
        script_id: The script ID
        db: Database session

    Returns:
        ScriptResponse
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


@router.get("/project/{project_id}", response_model=ScriptResponse)
async def get_project_script(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the script for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        ScriptResponse
    """
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script
