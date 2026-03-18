# backend/app/api/mobile.py
"""Mobile-specific API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


class MobileProjectResponse(BaseModel):
    """移动端项目响应（精简字段）"""
    id: str
    title: str
    status: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[MobileProjectResponse]
    total: int
    page: int
    page_size: int


class DashboardSummary(BaseModel):
    """Dashboard摘要"""
    total_projects: int
    active_projects: int
    completed_projects: int
    draft_projects: int


@router.get("/projects", response_model=PaginatedResponse)
async def get_mobile_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    移动端项目列表（分页、精简字段）

    Args:
        page: 页码
        page_size: 每页数量
        status: 状态过滤
        db: 数据库会话
        current_user: 当前用户

    Returns:
        分页项目列表
    """
    query = db.query(Project).filter(Project.owner_id == current_user.id)

    # 状态过滤
    if status:
        query = query.filter(Project.status == status)

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    projects = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[MobileProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/dashboard", response_model=DashboardSummary)
async def get_mobile_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    移动端Dashboard摘要

    Args:
        db: 数据库会话
        current_user: 当前用户

    Returns:
        项目统计摘要
    """
    total = db.query(Project).filter(Project.owner_id == current_user.id).count()
    active = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.status == "active"
    ).count()
    completed = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.status == "completed"
    ).count()
    draft = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.status == "draft"
    ).count()

    return DashboardSummary(
        total_projects=total,
        active_projects=active,
        completed_projects=completed,
        draft_projects=draft
    )


@router.post("/projects/{project_id}/quick-start")
async def quick_start_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    快速启动项目

    Args:
        project_id: 项目ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        更新后的项目
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # 快速启动：设置状态为active
    project.status = "active"
    db.commit()
    db.refresh(project)

    return {"success": True, "project_id": project.id, "status": project.status}


@router.get("/projects/{project_id}", response_model=MobileProjectResponse)
async def get_mobile_project_detail(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    移动端项目详情（精简版）

    Args:
        project_id: 项目ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        项目详情
    """
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return MobileProjectResponse.model_validate(project)
