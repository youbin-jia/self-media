# plugins/material_sources/example_source.py
from typing import List, Dict, Any
from plugins.material_sources.base import MaterialSourcePlugin


class ExampleMaterialSource(MaterialSourcePlugin):
    """示例素材源插件"""

    name = "example_source"
    version = "1.0.0"
    description = "Example material source plugin for demonstration"
    author = "Developer"
    supported_types = ["image"]

    async def collect(self, keyword: str, count: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """收集示例素材"""
        # 这是一个示例实现，返回模拟数据
        results = []

        for i in range(count):
            results.append({
                "url": f"https://example.com/images/{keyword}_{i}.jpg",
                "type": "image",
                "title": f"{keyword} image {i}",
                "description": f"Example image for keyword: {keyword}",
                "thumbnail_url": f"https://example.com/thumbnails/{keyword}_{i}_thumb.jpg",
                "metadata": {
                    "width": 1920,
                    "height": 1080,
                    "format": "jpg",
                    "source": "example"
                }
            })

        return results
