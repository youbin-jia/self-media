# backend/app/api/materials.py
"""Material API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.material import Material
from app.models.project import Project
from app.schemas.material import MaterialCreate, MaterialResponse, MaterialWithTagSearch
from app.services.material_collector import MaterialCollector
from app.utils.deduplication import MaterialDeduplicator

router = APIRouter()


@router.post("/collect", response_model=List[MaterialResponse])
async def collect_materials(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Collect materials for a project

    Extracts keywords from the project's topic_title and searches for images.

    Args:
        project_id: The project ID to collect materials for
        db: Database session

    Returns:
        List of collected materials

    Raises:
        HTTPException: 404 if project not found
    """
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Initialize collector
    collector = MaterialCollector()

    # Extract keywords from topic_title
    topic_title = project.topic_title or project.title
    keywords = collector.extract_keywords(topic_title)

    # Build search query from keywords
    query = " ".join(keywords) if keywords else topic_title

    # Search for images
    images = await collector.search_images(query, per_page=10)

    # Create material records
    materials = []
    for img in images:
        material = Material(
            id=img.get("id") or str(__import__('uuid').uuid4()),
            project_id=project_id,
            type=img.get("type", "image"),
            source=img.get("source", "unknown"),
            source_url=img.get("source_url"),
            local_path=None,  # Will be set after download
            material_metadata={
                "thumbnail_url": img.get("thumbnail_url"),
                "width": img.get("width"),
                "height": img.get("height"),
                "photographer": img.get("photographer"),
                "photographer_url": img.get("photographer_url"),
                "avg_color": img.get("avg_color"),
                "alt": img.get("alt")
            }
        )

        db.add(material)
        materials.append(material)

    db.commit()

    # Refresh to get created_at timestamps
    for material in materials:
        db.refresh(material)

    # Build response with metadata mapping
    result = []
    for material in materials:
        material_dict = {
            "id": material.id,
            "project_id": material.project_id,
            "type": material.type,
            "source": material.source,
            "source_url": material.source_url,
            "local_path": material.local_path,
            "metadata": material.material_metadata,
            "created_at": material.created_at
        }
        result.append(MaterialResponse(**material_dict))

    return result


@router.get("/project/{project_id}", response_model=List[MaterialResponse])
async def get_project_materials(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all materials for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        List of materials for the project

    Raises:
        HTTPException: 404 if project not found
    """
    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get materials
    materials = db.query(Material).filter(
        Material.project_id == project_id
    ).order_by(Material.created_at.desc()).all()

    # Build response with metadata mapping
    result = []
    for material in materials:
        material_dict = {
            "id": material.id,
            "project_id": material.project_id,
            "type": material.type,
            "source": material.source,
            "source_url": material.source_url,
            "local_path": material.local_path,
            "metadata": material.material_metadata,
            "created_at": material.created_at
        }
        result.append(MaterialResponse(**material_dict))

    return result


@router.post("/search")
async def search_materials(
    search: MaterialWithTagSearch,
    db: Session = Depends(get_db)
):
    """
    Search materials by tags

    Args:
        search: Search parameters with tags, material_type, and min_quality_score
        db: Database session

    Returns:
        List of materials matching the search criteria
    """
    query = db.query(Material).filter(Material.tags.contains(search.tags))

    if search.material_type:
        query = query.filter(Material.material_type == search.material_type)

    if search.min_quality_score:
        query = query.filter(Material.quality_score >= search.min_quality_score)

    materials = query.limit(search.limit).all()
    return {"materials": materials}


@router.get("/{material_id}/similar")
async def find_similar_materials(
    material_id: str,
    threshold: float = 0.7,
    db: Session = Depends(get_db)
):
    """
    Find similar materials

    Args:
        material_id: The material ID to find similar materials for
        threshold: Similarity threshold (0-1)
        db: Database session

    Returns:
        Material and list of similar materials with similarity scores

    Raises:
        HTTPException: 404 if material not found
    """
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    similar = MaterialDeduplicator.find_similar_materials(db, material, threshold)
    return {
        "material": material,
        "similar_materials": [
            {"material": m, "similarity": sim}
            for m, sim in similar
        ]
    }
