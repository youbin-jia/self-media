# backend/app/services/plugins/discovery.py
import os
import importlib
import inspect
from typing import List, Dict, Any
from pathlib import Path


class PluginDiscovery:
    """插件自动发现机制"""

    def __init__(self, plugin_dir: str = "plugins"):
        """
        初始化插件发现器

        Args:
            plugin_dir: 插件目录路径
        """
        self.plugin_dir = plugin_dir

    def discover_plugins(self) -> List[Dict[str, Any]]:
        """
        发现所有插件

        Returns:
            插件信息列表
        """
        discovered_plugins = []

        # 遍历插件目录
        plugin_path = Path(self.plugin_dir)

        if not plugin_path.exists():
            return discovered_plugins

        for category_dir in plugin_path.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name  # material_sources, llm_providers, etc.

            # 遍历类别目录中的插件
            for plugin_file in category_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                plugin_info = self._inspect_plugin_file(category, plugin_file)

                if plugin_info:
                    discovered_plugins.append(plugin_info)

        return discovered_plugins

    def _inspect_plugin_file(self, category: str, plugin_file: Path) -> Dict[str, Any]:
        """
        检查插件文件

        Args:
            category: 插件类别
            plugin_file: 插件文件路径

        Returns:
            插件信息字典
        """
        # 构建模块路径
        module_name = plugin_file.stem
        module_path = f"plugins.{category}.{module_name}"

        try:
            # 导入模块
            module = importlib.import_module(module_path)

            # 查找插件类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 检查是否是插件类（不是基类）
                if self._is_plugin_class(obj):
                    return {
                        "name": obj.name,
                        "version": obj.version,
                        "description": getattr(obj, 'description', ''),
                        "author": getattr(obj, 'author', ''),
                        "type": self._get_plugin_type(obj),
                        "module_path": module_path,
                        "class_name": name,
                        "file_path": str(plugin_file)
                    }

        except Exception as e:
            print(f"Error loading plugin {module_path}: {e}")

        return None

    def _is_plugin_class(self, obj) -> bool:
        """
        检查是否是插件类

        Args:
            obj: 类对象

        Returns:
            是否是插件类
        """
        # 检查是否有name和version属性
        return (
            hasattr(obj, 'name') and
            hasattr(obj, 'version') and
            not obj.__module__.endswith('.base')  # 不是基类
        )

    def _get_plugin_type(self, obj) -> str:
        """
        获取插件类型

        Args:
            obj: 插件类

        Returns:
            插件类型
        """
        # 根据基类判断类型
        try:
            from plugins.material_sources.base import MaterialSourcePlugin

            if issubclass(obj, MaterialSourcePlugin):
                return "material_source"
        except ImportError:
            pass

        return "unknown"
