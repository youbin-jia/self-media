# backend/tests/test_comprehensive_quality.py
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
import sys

# Mock cv2 at import time
sys.modules['cv2'] = Mock()

from app.services.quality_detector import QualityDetector


class TestComprehensiveQuality:
    """测试综合质量检测"""

    @pytest.mark.asyncio
    async def test_detect_comprehensive_quality(self):
        """测试综合质量检测"""
        mock_db = Mock()
        mock_project = Mock()
        mock_project.id = 1
        mock_project.script = Mock()
        mock_project.script.full_script = "测试脚本内容" * 100
        mock_project.script.segments = [
            {"type": "intro"},
            {"type": "body"},
            {"type": "outro"}
        ]
        mock_project.materials = []
        mock_project.output_path = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        detector = QualityDetector()
        result = await detector.detect_comprehensive_quality(1, mock_db)

        assert "overall_score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_detect_script_quality(self):
        """测试脚本质量检测"""
        mock_project = Mock()
        mock_script = Mock()
        mock_script.full_script = "这是测试脚本。" * 50
        mock_script.segments = [
            {"type": "intro"},
            {"type": "body"},
            {"type": "body"},
            {"type": "outro"}
        ]
        mock_project.script = mock_script

        detector = QualityDetector()
        result = await detector._detect_script_quality(mock_project)

        assert "score" in result
        assert "max_score" in result
        assert "metrics" in result
        assert result["score"] > 0

    def test_evaluate_structure(self):
        """测试结构评估"""
        mock_script = Mock()
        mock_script.segments = [
            {"type": "intro"},
            {"type": "body"},
            {"type": "body"},
            {"type": "outro"}
        ]

        detector = QualityDetector()
        result = detector._evaluate_structure(mock_script)

        assert result["score"] >= 19  # Good structure: 8 (intro) + min(10, 4) (2 bodies) + 7 (outro) = 19

    def test_evaluate_structure_missing_intro(self):
        """测试缺少开头"""
        mock_script = Mock()
        mock_script.segments = [
            {"type": "body"},
            {"type": "outro"}
        ]

        detector = QualityDetector()
        result = detector._evaluate_structure(mock_script)

        assert "缺少明确的开头" in result["issues"]

    def test_evaluate_content(self):
        """测试内容评估"""
        mock_script = Mock()
        mock_script.full_script = "测试内容" * 500  # Long enough

        detector = QualityDetector()
        result = detector._evaluate_content(mock_script)

        assert result["score"] > 15  # Should have base score

    def test_evaluate_content_too_short(self):
        """测试内容过短"""
        mock_script = Mock()
        mock_script.full_script = "短内容"

        detector = QualityDetector()
        result = detector._evaluate_content(mock_script)

        assert any("过短" in issue for issue in result["issues"])

    def test_evaluate_language(self):
        """测试语言评估"""
        mock_script = Mock()
        mock_script.full_script = "这是一个正常的句子。另一个句子也在其中。"

        detector = QualityDetector()
        result = detector._evaluate_language(mock_script)

        assert result["score"] >= 15  # Base score

    def test_evaluate_engagement(self):
        """测试吸引力评估"""
        mock_script = Mock()
        mock_script.full_script = "欢迎关注我们的频道！请点赞评论分享你的看法。"

        detector = QualityDetector()
        result = detector._evaluate_engagement(mock_script)

        assert result["score"] > 10  # Should have engagement keywords

    @pytest.mark.asyncio
    async def test_detect_video_quality(self):
        """测试视频质量检测"""
        mock_project = Mock()
        mock_project.output_path = "/tmp/test.mp4"

        # Mock Path.exists to return True
        with patch('pathlib.Path.exists', return_value=True):
            # Create mock cv2.VideoCapture instance
            import cv2
            mock_instance = Mock()
            cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            mock_instance.get.side_effect = [1920, 1080, 30.0, 3000]  # width, height, fps, frame_count
            mock_instance.release = Mock()

            detector = QualityDetector()
            result = await detector._detect_video_quality(mock_project)

            assert "score" in result
            assert "metrics" in result
            assert result["metrics"]["resolution"] == "1920x1080"

    @pytest.mark.asyncio
    async def test_detect_video_quality_low_resolution(self):
        """测试低分辨率视频"""
        mock_project = Mock()
        mock_project.output_path = "/tmp/test.mp4"

        # Mock Path.exists to return True
        with patch('pathlib.Path.exists', return_value=True):
            # Create mock cv2.VideoCapture instance
            import cv2
            mock_instance = Mock()
            cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            mock_instance.get.side_effect = [640, 480, 24.0, 1000]
            mock_instance.release = Mock()

            detector = QualityDetector()
            result = await detector._detect_video_quality(mock_project)

            assert any("分辨率较低" in issue for issue in result["issues"])

    def test_generate_overall_recommendations(self):
        """测试生成整体建议"""
        detector = QualityDetector()

        script_quality = {"score": 90}
        audio_quality = {"score": 90}
        video_quality = {"score": 90}

        recommendations = detector._generate_overall_recommendations(
            script_quality,
            audio_quality,
            video_quality
        )

        assert any("优秀" in rec for rec in recommendations)

    def test_generate_overall_recommendations_needs_improvement(self):
        """测试需要改进的建议"""
        detector = QualityDetector()

        script_quality = {"score": 50}
        audio_quality = {"score": 50}
        video_quality = {"score": 50}

        recommendations = detector._generate_overall_recommendations(
            script_quality,
            audio_quality,
            video_quality
        )

        assert any("需要改进" in rec for rec in recommendations)


class TestQualityGrades:
    """测试质量等级"""

    def test_grade_A(self):
        """测试A级"""
        detector = QualityDetector()
        grade = detector._calculate_grade(90)
        assert grade == "A"  # 90 >= 90

    def test_grade_B(self):
        """测试B级"""
        detector = QualityDetector()
        grade = detector._calculate_grade(80)
        assert grade == "B"  # 80 >= 75

    def test_grade_C(self):
        """测试C级"""
        detector = QualityDetector()
        grade = detector._calculate_grade(70)
        assert grade == "C"  # 70 >= 60

    def test_grade_D(self):
        """测试D级"""
        detector = QualityDetector()
        grade = detector._calculate_grade(50)
        assert grade == "D"  # 50 >= 45

    def test_grade_E(self):
        """测试E级"""
        detector = QualityDetector()
        grade = detector._calculate_grade(30)
        assert grade == "E"  # 30 >= 0


class TestScriptQualityMethods:
    """测试脚本质量检测的各个方法"""

    def test_evaluate_structure_no_segments(self):
        """测试无脚本片段的结构评估"""
        mock_script = Mock()
        mock_script.segments = []
        mock_script.full_script = None  # No full_script either

        detector = QualityDetector()
        result = detector._evaluate_structure(mock_script)

        # When both segments and full_script are empty/None, it will still
        # try to parse and give partial score for having "body"
        assert result["score"] >= 0  # Just check it runs without error
        assert len(result["issues"]) > 0  # Should have issues

    def test_evaluate_content_empty(self):
        """测试空内容评估"""
        mock_script = Mock()
        mock_script.full_script = None

        detector = QualityDetector()
        result = detector._evaluate_content(mock_script)

        assert result["score"] == 0
        assert "脚本内容为空" in result["issues"]

    def test_evaluate_content_too_long(self):
        """测试内容过长"""
        mock_script = Mock()
        mock_script.full_script = "测试内容" * 2000  # 8000 chars, > 5000

        detector = QualityDetector()
        result = detector._evaluate_content(mock_script)

        assert any("过长" in issue for issue in result["issues"])

    def test_evaluate_content_with_data(self):
        """测试包含数据的内容"""
        mock_script = Mock()
        # Make it long enough to avoid length penalty, include data and sources
        mock_script.full_script = "据数据显示，今年增长了50%。据悉，这是一个重要突破。" * 50  # ~1200 chars

        detector = QualityDetector()
        result = detector._evaluate_content(mock_script)

        # Should get bonus points for data and sources: 15 (base) + 5 (length) + 5 (digits) + 5 (sources) = 30
        assert result["score"] >= 25

    def test_evaluate_language_empty(self):
        """测试空语言评估"""
        mock_script = Mock()
        mock_script.full_script = None

        detector = QualityDetector()
        result = detector._evaluate_language(mock_script)

        assert result["score"] >= 15  # Base score

    def test_evaluate_language_long_sentences(self):
        """测试过长句子"""
        mock_script = Mock()
        # Create text with very long sentences (no sentence breaks)
        # After split by '。！？', we get one long sentence
        # A sentence longer than 60 chars should trigger the issue
        mock_script.full_script = "这是第一个超长的句子用来测试句子长度检测功能是否正常工作" * 3  # Multiple of same sentence

        detector = QualityDetector()
        result = detector._evaluate_language(mock_script)

        # Average sentence length will be very high (> 60)
        # Check score decreased or issues present
        assert result["score"] < 25  # Should be penalized

    def test_evaluate_engagement_empty(self):
        """测试空吸引力评估"""
        mock_script = Mock()
        mock_script.full_script = None

        detector = QualityDetector()
        result = detector._evaluate_engagement(mock_script)

        assert result["score"] >= 10  # Base score

    def test_evaluate_engagement_no_keywords(self):
        """测试缺少互动元素"""
        mock_script = Mock()
        mock_script.full_script = "这是一个普通的描述性内容。"

        detector = QualityDetector()
        result = detector._evaluate_engagement(mock_script)

        assert "缺少互动元素" in result["issues"]


class TestAudioQualityDetection:
    """测试音频质量检测"""

    @pytest.mark.asyncio
    async def test_detect_audio_quality_no_audio(self):
        """测试无音频文件"""
        mock_project = Mock()
        mock_project.materials = []

        detector = QualityDetector()
        result = await detector._detect_audio_quality(mock_project)

        assert result["score"] == 50
        assert "无音频文件" in result["issues"]

    @pytest.mark.asyncio
    async def test_detect_audio_quality_no_path(self):
        """测试音频无路径"""
        mock_project = Mock()
        mock_material = Mock()
        mock_material.material_type = "audio"
        mock_material.local_path = None
        mock_project.materials = [mock_material]

        detector = QualityDetector()
        result = await detector._detect_audio_quality(mock_project)

        assert result["score"] == 50
        assert "音频文件路径无效" in result["issues"]


class TestVideoQualityDetection:
    """测试视频质量检测"""

    @pytest.mark.asyncio
    async def test_detect_video_quality_no_video(self):
        """测试无视频文件"""
        mock_project = Mock()
        mock_project.output_path = None

        detector = QualityDetector()
        result = await detector._detect_video_quality(mock_project)

        assert result["score"] == 50
        assert "视频未生成" in result["issues"]

    @pytest.mark.asyncio
    async def test_detect_video_quality_file_not_exists(self):
        """测试视频文件不存在"""
        mock_project = Mock()
        mock_project.output_path = "/tmp/nonexistent.mp4"

        with patch('pathlib.Path.exists', return_value=False):
            detector = QualityDetector()
            result = await detector._detect_video_quality(mock_project)

            assert result["score"] == 50
            assert "视频未生成" in result["issues"]

    @pytest.mark.asyncio
    async def test_detect_video_quality_low_fps(self):
        """测试低帧率视频"""
        mock_project = Mock()
        mock_project.output_path = "/tmp/test.mp4"

        with patch('pathlib.Path.exists', return_value=True):
            import cv2
            mock_instance = Mock()
            cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            mock_instance.get.side_effect = [1920, 1080, 20.0, 1000]  # Low FPS
            mock_instance.release = Mock()

            detector = QualityDetector()
            result = await detector._detect_video_quality(mock_project)

            assert any("帧率较低" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_detect_video_quality_short_duration(self):
        """测试短视频"""
        mock_project = Mock()
        mock_project.output_path = "/tmp/test.mp4"

        with patch('pathlib.Path.exists', return_value=True):
            import cv2
            mock_instance = Mock()
            cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            # width, height, fps, frame_count = 20 seconds
            mock_instance.get.side_effect = [1920, 1080, 30.0, 600]
            mock_instance.release = Mock()

            detector = QualityDetector()
            result = await detector._detect_video_quality(mock_project)

            assert any("时长较短" in issue for issue in result["issues"])


class TestComprehensiveQualityIntegration:
    """测试综合质量检测集成"""

    @pytest.mark.asyncio
    async def test_detect_comprehensive_quality_no_project(self):
        """测试项目不存在"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        detector = QualityDetector()
        with pytest.raises(ValueError, match="Project .* not found"):
            await detector.detect_comprehensive_quality(999, mock_db)

    @pytest.mark.asyncio
    async def test_detect_comprehensive_quality_no_script(self):
        """测试无脚本的综合质量检测"""
        mock_db = Mock()
        mock_project = Mock()
        mock_project.id = 1
        mock_project.script = None
        mock_project.materials = []
        mock_project.output_path = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        detector = QualityDetector()
        result = await detector.detect_comprehensive_quality(1, mock_db)

        assert "overall_score" in result
        assert result["breakdown"]["script"]["score"] == 0
        assert "脚本未生成" in result["breakdown"]["script"]["issues"]


class TestIssueCollection:
    """测试问题收集"""

    def test_collect_issues(self):
        """测试收集所有问题"""
        detector = QualityDetector()

        quality_reports = [
            {"issues": ["问题1", "问题2"], "component": "script"},
            {"issues": ["问题3"], "component": "audio"},
            {"issues": [], "component": "video"}
        ]

        all_issues = detector._collect_issues(quality_reports)

        assert len(all_issues) == 3
        assert all_issues[0] == {"issue": "问题1", "component": "script"}
        assert all_issues[1] == {"issue": "问题2", "component": "script"}
        assert all_issues[2] == {"issue": "问题3", "component": "audio"}
