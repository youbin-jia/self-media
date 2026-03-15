# backend/app/api/projects.py
"""Project API Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(
        None,
        description="Filter by project status"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of projects to skip"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of projects to return"
    ),
    db: Session = Depends(get_db)
):
    """
    List projects with optional filtering and pagination

    Args:
        status: Optional status filter
        offset: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of projects
    """
    query = db.query(Project)

    if status:
        query = query.filter(Project.status == status)

    query = query.order_by(Project.created_at.desc())
    projects = query.offset(offset).limit(limit).all()

    # Map project_metadata to metadata for response
    result = []
    for project in projects:
        project_dict = {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "current_step": project.current_step,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "topic_source": project.topic_source,
            "topic_title": project.topic_title,
            "topic_hot_score": project.topic_hot_score,
            "metadata": project.project_metadata
        }
        result.append(ProjectResponse(**project_dict))

    return result


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new project

    Args:
        project_in: Project creation data
        db: Database session

    Returns:
        Created project
    """
    project = Project(
        title=project_in.title,
        topic_source=project_in.topic_source,
        topic_title=project_in.topic_title,
        topic_hot_score=project_in.topic_hot_score,
        project_metadata=project_in.metadata,
        status="pending",
        current_step="topic_selection"
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a project by ID

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Project data

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a project

    Args:
        project_id: The project ID
        project_in: Project update data
        db: Database session

    Returns:
        Updated project

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields if provided
    if project_in.title is not None:
        project.title = project_in.title
    if project_in.status is not None:
        project.status = project_in.status
    if project_in.current_step is not None:
        project.current_step = project_in.current_step
    if project_in.metadata is not None:
        project.project_metadata = project_in.metadata

    db.commit()
    db.refresh(project)

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"success": True, "message": "Project deleted successfully"}
