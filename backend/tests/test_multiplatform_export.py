# backend/tests/test_multiplatform_export.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.video_synthesizer import VideoSynthesizer


class TestMultiPlatformExport:
    """测试多平台导出"""

    def test_platform_configs_exist(self):
        """测试平台配置存在"""
        assert "horizontal" in VideoSynthesizer.PLATFORM_CONFIGS
        assert "vertical" in VideoSynthesizer.PLATFORM_CONFIGS
        assert "square" in VideoSynthesizer.PLATFORM_CONFIGS

    def test_horizontal_resolution(self):
        """测试横屏分辨率"""
        config = VideoSynthesizer.PLATFORM_CONFIGS["horizontal"]
        assert config["resolution"] == (1920, 1080)
        assert config["fps"] == 30

    def test_vertical_resolution(self):
        """测试竖屏分辨率"""
        config = VideoSynthesizer.PLATFORM_CONFIGS["vertical"]
        assert config["resolution"] == (1080, 1920)

    @pytest.mark.asyncio
    async def test_export_for_platform_horizontal(self, tmp_path):
        """测试导出横屏格式"""
        mock_clip = Mock()
        mock_clip.size = (1920, 1080)
        mock_clip.write_videofile = Mock()

        synthesizer = VideoSynthesizer()
        output_path = str(tmp_path / "output.mp4")

        result = synthesizer.export_for_platform(
            mock_clip,
            "horizontal",
            output_path
        )

        mock_clip.write_videofile.assert_called_once()
        assert result == output_path

    @pytest.mark.asyncio
    async def test_export_for_platform_vertical(self, tmp_path):
        """测试导出竖屏格式"""
        mock_clip = Mock()
        mock_clip.size = (1920, 1080)

        with patch.object(VideoSynthesizer, '_adapt_aspect_ratio') as mock_adapt:
            mock_adapt.return_value = mock_clip
            mock_clip.write_videofile = Mock()

            synthesizer = VideoSynthesizer()
            output_path = str(tmp_path / "output.mp4")

            result = synthesizer.export_for_platform(
                mock_clip,
                "vertical",
                output_path
            )

            # Should adapt aspect ratio for vertical
            mock_adapt.assert_called_once_with(mock_clip, 1080, 1920)
            assert result == output_path

    @pytest.mark.asyncio
    async def test_adapt_aspect_ratio_wider_source(self):
        """测试宽屏源适配到竖屏"""
        mock_clip = Mock()
        mock_clip.w = 1920
        mock_clip.h = 1080
        mock_clip.crop = Mock(return_value=mock_clip)
        mock_clip.resize = Mock(return_value=mock_clip)

        synthesizer = VideoSynthesizer()
        result = synthesizer._adapt_aspect_ratio(mock_clip, 1080, 1920)

        # Should crop horizontally
        mock_clip.crop.assert_called_once()

    @pytest.mark.asyncio
    async def test_adapt_aspect_ratio_taller_source(self):
        """测试竖屏源适配到横屏"""
        mock_clip = Mock()
        mock_clip.w = 1080
        mock_clip.h = 1920
        mock_clip.crop = Mock(return_value=mock_clip)
        mock_clip.resize = Mock(return_value=mock_clip)

        synthesizer = VideoSynthesizer()
        result = synthesizer._adapt_aspect_ratio(mock_clip, 1920, 1080)

        # Should crop vertically
        mock_clip.crop.assert_called_once()


class TestMultiPlatformTask:
    """测试多平台Celery任务"""

    @pytest.mark.asyncio
    async def test_synthesize_multiplatform_task(self):
        """测试多平台合成任务"""
        from app.tasks.video_tasks import synthesize_video_task

        with patch('app.tasks.video_tasks.VideoSynthesizer') as mock_synth:
            with patch('app.tasks.video_tasks.current_task'):
                with patch('app.tasks.video_tasks.SessionLocal') as mock_session:
                    with patch('moviepy.editor.VideoFileClip') as mock_video_clip:
                        # Mock database
                        mock_db = Mock()
                        mock_session.return_value = mock_db

                        # Mock project
                        mock_project = Mock()
                        mock_project.id = "test-project-1"
                        mock_project.project_metadata = {"materials": [{"local_path": "/tmp/test.mp4"}]}
                        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

                        # Mock synthesizer
                        mock_instance = Mock()
                        mock_synth.return_value = mock_instance
                        mock_instance.synthesize = Mock(return_value="/tmp/output.mp4")
                        mock_instance.get_output_path = Mock(return_value="/tmp/output_horizontal.mp4")

                        # Mock video clip
                        mock_clip = Mock()
                        mock_video_clip.return_value = mock_clip
                        mock_clip.close = Mock()

                        mock_instance.export_for_platform = Mock()

                        # Run task
                        result = synthesize_video_task(
                            project_id="test-project-1",
                            platforms=["horizontal", "vertical"]
                        )

                        assert result["status"] == "success"
                        assert "horizontal" in result["outputs"]
                        assert "vertical" in result["outputs"]
