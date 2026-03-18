# plugins/material_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class MaterialSourcePlugin(ABC):
    """素材源插件基类"""

    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    supported_types: List[str] = []  # ["image", "video", "audio"]
    config: Dict[str, Any] = {}

    @abstractmethod
    async def collect(self, keyword: str, count: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        收集素材

        Args:
            keyword: 搜索关键词
            count: 需要的素材数量
            **kwargs: 其他参数（如material_type, orientation等）

        Returns:
            素材列表，每个素材包含:
            {
                "url": str,
                "type": str,  # "image", "video", "audio"
                "title": str,
                "description": str,
                "thumbnail_url": str,
                "metadata": dict
            }
        """
        pass

    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置插件

        Args:
            config: 配置字典
        """
        self.config = config

    def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            配置是否有效
        """
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取插件元数据

        Returns:
            元数据字典
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "supported_types": self.supported_types
        }
