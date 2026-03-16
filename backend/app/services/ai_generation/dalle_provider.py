# backend/app/services/ai_generation/dalle_provider.py
from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
import httpx
from pathlib import Path
import os
from .base import AIGenerationProvider


class DALLEProvider(AIGenerationProvider):
    """DALL-E 3图像生成（默认选项）"""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "dalle"

    @property
    def capabilities(self) -> List[str]:
        return ["image_generation"]

    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: tuple = (1920, 1080),
        **kwargs
    ) -> Dict[str, Any]:
        """使用DALL-E 3生成图像"""

        # 转换尺寸到DALL-E支持的格式
        dalle_size = self._map_size(size)

        # 增强提示词
        enhanced_prompt = self._enhance_prompt(prompt, style)

        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=dalle_size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url

            # 下载图像
            image_path = await self._download_image(image_url)

            return {
                "success": True,
                "image_path": image_path,
                "provider": self.provider_name,
                "metadata": {
                    "prompt": enhanced_prompt,
                    "size": size,
                    "style": style
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider_name
            }

    async def generate_music(
        self,
        script_context: dict,
        duration: float,
        mood: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """DALL-E不支持音乐生成"""
        return {
            "success": False,
            "error": "DALL-E does not support music generation",
            "provider": self.provider_name
        }

    def _map_size(self, size: tuple) -> str:
        """映射尺寸到DALL-E支持格式"""
        width, height = size
        if width > height:
            return "1792x1024"  # Landscape
        elif height > width:
            return "1024x1792"  # Portrait
        else:
            return "1024x1024"  # Square

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """增强提示词"""
        style_keywords = {
            "realistic": "photorealistic, highly detailed, professional photography",
            "artistic": "artistic, creative, stylized, illustration",
            "cinematic": "cinematic, dramatic lighting, movie scene, epic composition"
        }

        keywords = style_keywords.get(style, "")
        return f"{prompt}, {keywords}" if keywords else prompt

    async def _download_image(self, url: str) -> str:
        """下载生成的图像"""
        # 创建保存目录
        save_dir = Path("data/generated/images")
        save_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        import uuid
        filename = f"{uuid.uuid4()}.png"
        save_path = save_dir / filename

        # 下载图像
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

        return str(save_path)
