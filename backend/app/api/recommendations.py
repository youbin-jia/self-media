# backend/app/api/recommendations.py
"""Recommendation API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.project import Project
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.recommendations.engine import RecommendationEngine

router = APIRouter()


@router.get("/topics")
async def get_topic_recommendations(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取话题推荐"""
    engine = RecommendationEngine()
    recommendations = engine.recommend_topics(current_user.id, db, limit=limit)
    return recommendations


@router.get("/popular")
async def get_popular_topics(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取热门话题"""
    engine = RecommendationEngine()
    popular = engine.get_popular_topics(db, limit=limit)
    return popular


@router.get("/similar/{project_id}")
async def get_similar_projects(
    project_id: str,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取相似项目推荐"""
    # 验证项目存在
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    engine = RecommendationEngine()
    similar = engine.find_similar_projects(project_id, db, limit=limit)

    # 转换为响应格式
    result = []
    for p in similar:
        result.append({
            "id": p.id,
            "title": p.title,
            "topic_source": p.topic_source,
            "topic_title": p.topic_title,
            "status": p.status
        })

    return result
