# backend/tests/test_material_collection_fault_tolerance.py
import pytest
import httpx
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from app.services.material_collector import MaterialCollector


class TestMaterialCollectionFaultTolerance:
    """测试素材采集容错"""

    @pytest.mark.asyncio
    async def test_collect_with_pexels_success(self):
        """测试Pexels采集成功"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_collect_from_pexels') as mock_pexels:
            mock_material = Mock()
            mock_pexels.return_value = [mock_material]

            result = await collector.collect_materials(
                query="nature",
                project_id=1,
                count=1,
                sources=["pexels"]
            )

            assert len(result) == 1
            mock_pexels.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_falls_back_to_next_source(self):
        """测试失败时降级到下一个源"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_collect_from_pexels') as mock_pexels:
            with patch.object(collector, '_collect_from_pixabay') as mock_pixabay:
                mock_pexels.side_effect = Exception("Pexels failed")
                mock_material = Mock()
                mock_pixabay.return_value = [mock_material]

                result = await collector.collect_materials(
                    query="nature",
                    project_id=1,
                    count=1,
                    sources=["pexels", "pixabay"]
                )

                assert len(result) == 1
                mock_pixabay.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_uses_fallback_when_all_fail(self):
        """测试所有源失败时使用后备素材"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_collect_from_pexels') as mock_pexels:
            with patch.object(collector, '_collect_from_pixabay') as mock_pixabay:
                with patch.object(collector, '_get_fallback_materials') as mock_fallback:
                    mock_pexels.side_effect = Exception("Pexels failed")
                    mock_pixabay.side_effect = Exception("Pixabay failed")
                    mock_material = Mock()
                    mock_fallback.return_value = [mock_material]

                    result = await collector.collect_materials(
                        query="nature",
                        project_id=1,
                        count=5,
                        sources=["pexels", "pixabay"]
                    )

                    assert len(result) == 1
                    mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_from_pixabay(self):
        """测试Pixabay采集"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.PIXABAY_API_KEY = "test_api_key"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json = Mock(return_value={
                    "hits": [
                        {
                            "id": 1,
                            "videos": {"large": {"url": "http://example.com/video.mp4"}},
                            "duration": 10
                        }
                    ]
                })

                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock()
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance

                with patch.object(collector, '_download_file') as mock_download:
                    mock_download.return_value = "/tmp/video.mp4"
                    mock_db.add = Mock()
                    mock_db.commit = Mock()

                    result = await collector._collect_from_pixabay("nature", 1, 5)

                    assert len(result) > 0

    @pytest.mark.asyncio
    async def test_collect_from_unsplash(self):
        """测试Unsplash采集"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.UNSPLASH_ACCESS_KEY = "test_api_key"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json = Mock(return_value={
                    "results": [
                        {
                            "id": "photo1",
                            "urls": {"regular": "http://example.com/photo.jpg"},
                            "width": 1920,
                            "height": 1080
                        }
                    ]
                })

                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock()
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance

                with patch.object(collector, '_download_file') as mock_download:
                    mock_download.return_value = "/tmp/photo.jpg"
                    mock_db.add = Mock()
                    mock_db.commit = Mock()

                    result = await collector._collect_from_unsplash("nature", 1, 5)

                    assert len(result) > 0
                    assert result[0].material_type == "image"

    def test_get_fallback_materials_from_library(self):
        """测试从后备素材库获取"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('pathlib.Path.exists') as mock_exists:
            with patch('pathlib.Path.glob') as mock_glob:
                mock_exists.return_value = True
                mock_file = Mock()
                mock_file.suffix = ".mp4"
                mock_glob.return_value = [mock_file]

                mock_db.add = Mock()
                mock_db.commit = Mock()

                result = collector._get_fallback_materials(1, 5)

                assert len(result) > 0

    def test_create_solid_color_materials(self, tmp_path):
        """测试创建纯色素材"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('moviepy.editor.ColorClip') as mock_clip:
            mock_instance = Mock()
            mock_clip.return_value = mock_instance
            mock_instance.write_videofile = Mock()

            mock_db.add = Mock()
            mock_db.commit = Mock()

            with patch('pathlib.Path.mkdir'):
                result = collector._create_solid_color_materials(1, 3)

                assert len(result) == 3
                mock_db.add.assert_called()


class TestMaterialCollectionEdgeCases:
    """测试素材采集边缘情况"""

    @pytest.mark.asyncio
    async def test_api_rate_limit_handling(self):
        """测试API速率限制处理"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.PIXABAY_API_KEY = "test_api_key"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 429  # Rate limit

                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock()
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance

                result = await collector._collect_from_pixabay("test", 1, 5)

                # Should handle gracefully and return empty
                assert result == []

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """测试网络超时处理"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.PIXABAY_API_KEY = "test_api_key"

            # Create a proper async context manager mock
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise httpx.TimeoutException("Timeout")

            with patch('httpx.AsyncClient', return_value=AsyncContextManagerMock()):
                result = await collector._collect_from_pixabay("test", 1, 5)

                # Should handle gracefully and return empty
                assert result == []
