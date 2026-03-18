# backend/app/services/plugins/loader.py
import importlib
from typing import Dict, Any, Type
from sqlalchemy.orm import Session

from app.models.plugin import Plugin, PluginConfiguration


class PluginLoader:
    """插件加载器"""

    def load_plugin_class(self, plugin_info: Dict[str, Any]) -> Type:
        """
        加载插件类

        Args:
            plugin_info: 插件信息

        Returns:
            插件类
        """
        module_path = plugin_info["module_path"]
        class_name = plugin_info["class_name"]

        # 导入模块
        module = importlib.import_module(module_path)

        # 获取插件类
        plugin_class = getattr(module, class_name)

        return plugin_class

    def register_plugin(
        self,
        plugin_info: Dict[str, Any],
        db: Session
    ) -> Plugin:
        """
        在数据库中注册插件

        Args:
            plugin_info: 插件信息
            db: 数据库会话

        Returns:
            Plugin实例
        """
        # 检查插件是否已存在
        existing_plugin = db.query(Plugin).filter(
            Plugin.name == plugin_info["name"]
        ).first()

        if existing_plugin:
            # 更新现有插件
            existing_plugin.version = plugin_info["version"]
            existing_plugin.description = plugin_info.get("description", "")
            existing_plugin.author = plugin_info.get("author", "")
            existing_plugin.type = plugin_info["type"]
            db.commit()
            return existing_plugin

        # 创建新插件
        plugin = Plugin(
            name=plugin_info["name"],
            type=plugin_info["type"],
            version=plugin_info["version"],
            description=plugin_info.get("description", ""),
            author=plugin_info.get("author", ""),
            enabled=False,  # 默认禁用，需要手动启用
            plugin_metadata={
                "module_path": plugin_info["module_path"],
                "class_name": plugin_info["class_name"],
                "file_path": plugin_info.get("file_path", "")
            }
        )

        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        return plugin

    def load_plugin_instance(
        self,
        plugin: Plugin,
        db: Session
    ) -> Any:
        """
        加载插件实例

        Args:
            plugin: Plugin模型实例
            db: 数据库会话

        Returns:
            插件实例
        """
        # 获取插件类
        plugin_info = {
            "module_path": plugin.plugin_metadata["module_path"],
            "class_name": plugin.plugin_metadata["class_name"]
        }

        plugin_class = self.load_plugin_class(plugin_info)

        # 创建实例
        instance = plugin_class()

        # 加载配置
        configurations = db.query(PluginConfiguration).filter(
            PluginConfiguration.plugin_id == plugin.id
        ).all()

        config = {config.key: config.value for config in configurations}
        instance.configure(config)

        return instance
