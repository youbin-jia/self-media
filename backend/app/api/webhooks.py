# backend/app/api/webhooks.py
"""Webhook management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.webhook import Webhook, WebhookDelivery
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    enabled: Optional[bool] = True


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    enabled: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: str
    name: str
    url: str
    events: List[str]
    enabled: bool

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str
    response_code: Optional[int]
    error_message: Optional[str]
    attempt_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出所有Webhooks"""
    webhooks = db.query(Webhook).all()
    return webhooks


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建Webhook"""
    webhook = Webhook(
        name=webhook_data.name,
        url=webhook_data.url,
        events=webhook_data.events,
        secret=webhook_data.secret,
        enabled=webhook_data.enabled
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取Webhook详情"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新Webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # 更新字段
    update_data = webhook_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(webhook, key, value)

    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除Webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    db.delete(webhook)
    db.commit()


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取Webhook投递记录"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.created_at.desc()).limit(50).all()

    return deliveries
