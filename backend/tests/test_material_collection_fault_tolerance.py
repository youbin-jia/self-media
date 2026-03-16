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


class TestPexelsAPIErrors:
    """测试Pexels API错误场景"""

    @pytest.mark.asyncio
    async def test_pexels_http_500_error(self):
        """测试Pexels HTTP 500错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.search_images("test", per_page=5)

            # Should fall back to mock data
            assert len(result) > 0
            assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_pexels_http_503_error(self):
        """测试Pexels HTTP 503错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 503

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.search_images("test", per_page=5)

            # Should fall back to mock data
            assert len(result) > 0
            assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_pexels_network_error(self):
        """测试Pexels网络错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            # Create context manager mock that raises error
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise httpx.RequestError("Network error")

            mock_client.return_value = AsyncContextManagerMock()

            result = await collector.search_images("test", per_page=5)

            # Should fall back to mock data
            assert len(result) > 0
            assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_pexels_http_status_error(self):
        """测试Pexels HTTP状态错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404

            # Create context manager mock
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    error = httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response)
                    raise error

            mock_client.return_value = AsyncContextManagerMock()

            result = await collector.search_images("test", per_page=5)

            # Should fall back to mock data
            assert len(result) > 0
            assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_pexels_unexpected_error(self):
        """测试Pexels意外错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            # Create context manager mock that raises error
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise RuntimeError("Unexpected error")

            mock_client.return_value = AsyncContextManagerMock()

            result = await collector.search_images("test", per_page=5)

            # Should fall back to mock data
            assert len(result) > 0
            assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_pexels_success_with_api_key(self):
        """测试Pexels成功调用（有API key）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "photos": [
                    {
                        "id": 123,
                        "src": {
                            "original": "http://example.com/photo.jpg",
                            "medium": "http://example.com/photo_medium.jpg"
                        },
                        "width": 1920,
                        "height": 1080,
                        "photographer": "Test Photographer",
                        "photographer_url": "http://example.com/@test",
                        "avg_color": "#FFFFFF",
                        "alt": "Test photo"
                    }
                ]
            })

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.search_images("nature", per_page=10)

            assert len(result) == 1
            assert result[0]["id"] == "123"
            assert result[0]["source"] == "pexels"
            assert result[0]["photographer"] == "Test Photographer"


class TestDownloadErrors:
    """测试下载错误场景"""

    @pytest.mark.asyncio
    async def test_download_material_http_error(self):
        """测试下载素材HTTP错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.download_material(
                "http://example.com/photo.jpg",
                "project1",
                "material1"
            )

            # Should return None on failure
            assert result is None

    @pytest.mark.asyncio
    async def test_download_material_network_error(self):
        """测试下载素材网络错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            # Create context manager mock that raises error
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise httpx.RequestError("Network error")

            mock_client.return_value = AsyncContextManagerMock()

            result = await collector.download_material(
                "http://example.com/photo.jpg",
                "project1",
                "material1"
            )

            # Should return None on failure
            assert result is None

    @pytest.mark.asyncio
    async def test_download_material_http_status_error(self):
        """测试下载素材HTTP状态错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("Server error", request=Mock(), response=mock_response))

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.download_material(
                "http://example.com/photo.jpg",
                "project1",
                "material1"
            )

            # Should return None on failure
            assert result is None

    @pytest.mark.asyncio
    async def test_download_material_io_error(self, tmp_path):
        """测试下载素材IO错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"
        collector.materials_dir = tmp_path

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake image data"

            # Create context manager mock
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    return mock_response

            mock_client.return_value = AsyncContextManagerMock()

            with patch('builtins.open', side_effect=IOError("Permission denied")):
                result = await collector.download_material(
                    "http://example.com/photo.jpg",
                    "project1",
                    "material1"
                )

                # Should return None on failure
                assert result is None

    @pytest.mark.asyncio
    async def test_download_material_unexpected_error(self):
        """测试下载素材意外错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            # Create context manager mock that raises error
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise RuntimeError("Unexpected error")

            mock_client.return_value = AsyncContextManagerMock()

            result = await collector.download_material(
                "http://example.com/photo.jpg",
                "project1",
                "material1"
            )

            # Should return None on failure
            assert result is None

    @pytest.mark.asyncio
    async def test_download_material_success(self, tmp_path):
        """测试下载素材成功"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"
        collector.materials_dir = tmp_path

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake image data"

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.download_material(
                "http://example.com/photo.jpg",
                "project1",
                "material1"
            )

            # Should return path to downloaded file
            assert result is not None
            assert "project1" in result
            assert "material1.jpg" in result


class TestDownloadFileMethod:
    """测试_download_file方法"""

    @pytest.mark.asyncio
    async def test_download_file_success(self, tmp_path):
        """测试_download_file成功"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.DATA_DIR = str(tmp_path)

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.content = b"test file content"

                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock()
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance

                result = await collector._download_file("http://example.com/video.mp4", 1)

                assert result is not None
                assert result.endswith(".mp4")

    @pytest.mark.asyncio
    async def test_download_file_http_error(self):
        """测试_download_file HTTP错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.DATA_DIR = "/tmp/test"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 404

                # Create context manager mock
                class AsyncContextManagerMock:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                    async def get(self, *args, **kwargs):
                        return mock_response

                mock_client.return_value = AsyncContextManagerMock()

                with pytest.raises(RuntimeError, match="Failed to download file"):
                    await collector._download_file("http://example.com/video.mp4", 1)


class TestCollectMaterialsEdgeCases:
    """测试collect_materials边缘情况"""

    @pytest.mark.asyncio
    async def test_collect_materials_stops_when_enough_collected(self):
        """测试collect_materials在收集足够时停止"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_collect_from_pexels') as mock_pexels:
            mock_materials = [Mock(), Mock(), Mock()]
            mock_pexels.return_value = mock_materials

            result = await collector.collect_materials(
                query="nature",
                project_id=1,
                count=3,
                sources=["pexels", "pixabay"]
            )

            assert len(result) == 3
            # Should only call pexels, not pixabay
            mock_pexels.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_materials_empty_sources(self):
        """测试collect_materials空源列表"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_get_fallback_materials') as mock_fallback:
            mock_fallback.return_value = [Mock()]

            result = await collector.collect_materials(
                query="nature",
                project_id=1,
                count=5,
                sources=[]
            )

            # Should use fallback
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_materials_unknown_source(self):
        """测试collect_materials未知源"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_get_fallback_materials') as mock_fallback:
            mock_fallback.return_value = [Mock()]

            result = await collector.collect_materials(
                query="nature",
                project_id=1,
                count=5,
                sources=["unknown_source"]
            )

            # Should use fallback since unknown source is skipped
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_materials_ai_generated_source(self):
        """测试collect_materials AI生成源（Phase 3占位符）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch.object(collector, '_get_fallback_materials') as mock_fallback:
            mock_fallback.return_value = [Mock()]

            result = await collector.collect_materials(
                query="nature",
                project_id=1,
                count=5,
                sources=["ai_generated"]
            )

            # Should use fallback since AI generation returns empty in Phase 2
            mock_fallback.assert_called_once()


class TestFallbackMaterialEdgeCases:
    """测试后备素材边缘情况"""

    def test_get_fallback_materials_empty_library(self):
        """测试后备素材库为空"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('pathlib.Path.glob') as mock_glob:
                mock_glob.return_value = []  # Empty library

                with patch.object(collector, '_create_solid_color_materials') as mock_create:
                    mock_create.return_value = [Mock()]

                    result = collector._get_fallback_materials(1, 5)

                    # Should create solid color materials
                    mock_create.assert_called_once()

    def test_get_fallback_materials_library_not_exists(self):
        """测试后备素材库不存在"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False

            with patch.object(collector, '_create_solid_color_materials') as mock_create:
                mock_create.return_value = [Mock()]

                result = collector._get_fallback_materials(1, 5)

                # Should create solid color materials
                mock_create.assert_called_once()


class TestUnsplashAPIErrors:
    """测试Unsplash API错误"""

    @pytest.mark.asyncio
    async def test_unsplash_api_error(self):
        """测试Unsplash API错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.UNSPLASH_ACCESS_KEY = "test_api_key"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 500

                # Create context manager mock
                class AsyncContextManagerMock:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                    async def get(self, *args, **kwargs):
                        return mock_response

                mock_client.return_value = AsyncContextManagerMock()

                with pytest.raises(RuntimeError, match="Unsplash API error"):
                    await collector._collect_from_unsplash("test", 1, 5)


class TestPixabayAPIErrors:
    """测试Pixabay API错误"""

    @pytest.mark.asyncio
    async def test_pixabay_api_error_500(self):
        """测试Pixabay API 500错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.PIXABAY_API_KEY = "test_api_key"

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 500

                # Create context manager mock
                class AsyncContextManagerMock:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, *args):
                        pass
                    async def get(self, *args, **kwargs):
                        return mock_response

                mock_client.return_value = AsyncContextManagerMock()

                with pytest.raises(RuntimeError, match="Pixabay API error"):
                    await collector._collect_from_pixabay("test", 1, 5)

    @pytest.mark.asyncio
    async def test_pixabay_network_request_error(self):
        """测试Pixabay网络请求错误"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        with patch('app.services.material_collector.settings') as mock_settings:
            mock_settings.PIXABAY_API_KEY = "test_api_key"

            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def get(self, *args, **kwargs):
                    raise httpx.RequestError("Network error")

            with patch('httpx.AsyncClient', return_value=AsyncContextManagerMock()):
                result = await collector._collect_from_pixabay("test", 1, 5)

                # Should handle gracefully and return empty
                assert result == []


class TestUtilityMethods:
    """测试工具方法"""

    def test_extract_keywords(self):
        """测试关键词提取"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        result = collector.extract_keywords("Beautiful Sunset Landscape", max_keywords=3)

        assert len(result) <= 3
        assert "Beautiful" in result or "Sunset" in result or "Landscape" in result

    def test_extract_keywords_chinese(self):
        """测试中文关键词提取"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        result = collector.extract_keywords("美丽的日落风景", max_keywords=3)

        assert len(result) <= 3
        # Should filter out stop words
        assert "的" not in result

    def test_extract_keywords_with_separators(self):
        """测试带分隔符的关键词提取"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        result = collector.extract_keywords("nature|landscape:sunset", max_keywords=5)

        assert len(result) > 0

    def test_extract_tags_list(self):
        """测试标签提取（列表格式）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        item = {
            "tags": ["nature", "landscape", "sunset"],
            "alt": "Beautiful sunset over mountains"
        }

        result = collector._extract_tags("nature", item)

        assert "nature" in result
        assert "landscape" in result

    def test_extract_tags_string(self):
        """测试标签提取（字符串格式）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        item = {
            "tags": "nature, landscape, sunset",
            "alt": "Beautiful sunset"
        }

        result = collector._extract_tags("sunset", item)

        assert "sunset" in result

    def test_extract_tags_no_tags(self):
        """测试标签提取（无标签字段）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)

        item = {
            "alt": "Beautiful sunset"
        }

        result = collector._extract_tags("test", item)

        assert "test" in result


class TestSearchImagesEdgeCases:
    """测试search_images边缘情况"""

    @pytest.mark.asyncio
    async def test_search_images_no_api_key(self):
        """测试search_images无API key"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = None

        result = await collector.search_images("test", per_page=10)

        # Should return mock images
        assert len(result) == 10
        assert result[0]["source"] == "mock"

    @pytest.mark.asyncio
    async def test_search_images_empty_response(self):
        """测试search_images空响应"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = "test_key"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"photos": []})

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await collector.search_images("test", per_page=10)

            # Should return empty list
            assert len(result) == 0


class TestDownloadMaterialEdgeCases:
    """测试download_material边缘情况"""

    @pytest.mark.asyncio
    async def test_download_material_no_api_key(self):
        """测试download_material无API key（mock模式）"""
        mock_db = Mock()
        collector = MaterialCollector(mock_db)
        collector.api_key = None

        result = await collector.download_material(
            "http://example.com/photo.jpg",
            "project1",
            "material1"
        )

        # Should return mock path
        assert result is not None
        assert "project1" in result
        assert "material1.jpg" in result
