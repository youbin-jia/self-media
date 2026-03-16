# backend/app/services/ai_generation/dalle_provider.py
import logging
import uuid
from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
import httpx
from pathlib import Path
from .base import AIGenerationProvider
from app.config import settings

logger = logging.getLogger(__name__)


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
        logger.info(f"Starting DALL-E image generation with prompt: {prompt[:50]}...")

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

            logger.info(f"DALL-E image generation successful: {image_path}")

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
            logger.error(f"DALL-E image generation failed: {str(e)}")
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
        """映射尺寸到DALL-E支持格式

        Returns:
            str: DALL-E supported size string (e.g., "1792x1024")
        """
        width, height = size
        if width > height:
            return "1792x1024"  # Landscape
        elif height > width:
            return "1024x1792"  # Portrait
        else:
            return "1024x1024"  # Square

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """增强提示词

        Returns:
            str: Enhanced prompt with style keywords
        """
        style_keywords = {
            "realistic": "photorealistic, highly detailed, professional photography",
            "artistic": "artistic, creative, stylized, illustration",
            "cinematic": "cinematic, dramatic lighting, movie scene, epic composition"
        }

        keywords = style_keywords.get(style, "")
        return f"{prompt}, {keywords}" if keywords else prompt

    async def _download_image(self, url: str) -> str:
        """下载生成的图像

        Returns:
            str: Local file path where image was saved

        Raises:
            httpx.HTTPError: If download fails
            IOError: If saving file fails
        """
        # 创建保存目录 - use settings.DATA_DIR
        save_dir = Path(settings.DATA_DIR) / "generated" / "images"
        save_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        filename = f"{uuid.uuid4()}.png"
        save_path = save_dir / filename

        # 下载图像 - with proper error handling
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(save_path, "wb") as f:
                    f.write(response.content)

            return str(save_path)
        except httpx.HTTPError as e:
            logger.error(f"Failed to download image from {url}: {str(e)}")
            raise
        except IOError as e:
            logger.error(f"Failed to save image to {save_path}: {str(e)}")
            raise
