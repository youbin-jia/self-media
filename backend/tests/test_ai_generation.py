# backend/tests/test_ai_generation.py
import pytest
from app.services.ai_generation.base import AIGenerationProvider


class TestAIGenerationProvider:
    """测试AI生成Provider抽象基类"""

    def test_base_provider_is_abstract(self):
        """基类不能直接实例化"""
        with pytest.raises(TypeError):
            AIGenerationProvider()

    def test_base_provider_requires_generate_image_method(self):
        """子类必须实现generate_image方法"""
        class IncompleteProvider(AIGenerationProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_all_abstract_methods(self):
        """子类必须实现所有抽象方法"""
        class IncompleteProvider(AIGenerationProvider):
            async def generate_image(self, prompt, style, size, **kwargs):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider()
