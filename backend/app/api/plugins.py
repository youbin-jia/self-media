# backend/app/api/plugins.py
"""Plugin management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models.plugin import Plugin, PluginConfiguration
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()


class PluginResponse(BaseModel):
    id: str
    name: str
    type: str
    version: str
    description: Optional[str]
    author: Optional[str]
    enabled: bool
    plugin_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class PluginConfigUpdate(BaseModel):
    configurations: Dict[str, str]


class PluginConfigResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[PluginResponse])
async def list_plugins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出所有插件"""
    plugins = db.query(Plugin).all()
    return plugins


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取插件详情"""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )

    return plugin


@router.post("/{plugin_id}/enable", response_model=PluginResponse)
async def enable_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启用插件"""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )

    plugin.enabled = True
    db.commit()
    db.refresh(plugin)

    return plugin


@router.post("/{plugin_id}/disable", response_model=PluginResponse)
async def disable_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """禁用插件"""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )

    plugin.enabled = False
    db.commit()
    db.refresh(plugin)

    return plugin


@router.put("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    config_data: PluginConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新插件配置"""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )

    # 更新配置
    for key, value in config_data.configurations.items():
        config = db.query(PluginConfiguration).filter(
            PluginConfiguration.plugin_id == plugin_id,
            PluginConfiguration.key == key
        ).first()

        if config:
            config.value = value
        else:
            config = PluginConfiguration(
                plugin_id=plugin_id,
                key=key,
                value=value
            )
            db.add(config)

    db.commit()

    return {"success": True, "message": "Configuration updated"}


@router.get("/{plugin_id}/config", response_model=List[PluginConfigResponse])
async def get_plugin_config(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取插件配置"""
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )

    configurations = db.query(PluginConfiguration).filter(
        PluginConfiguration.plugin_id == plugin_id
    ).all()

    return configurations
