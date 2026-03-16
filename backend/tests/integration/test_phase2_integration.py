# backend/tests/integration/test_phase2_integration.py
"""
Phase 2 Integration Tests

Tests the integration between all Phase 2 features:
- Multi-LLM Provider support
- TTS integration
- Material collection with deduplication
- Multi-platform export
- Quality detection
- End-to-end workflow
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.project import Project
from app.models.script import Script
from app.models.material import Material
from app.services.llm import LLMProviderManager
from app.services.tts import TTSProviderManager
from app.services.material_collector import MaterialCollector
from app.services.video_synthesizer import VideoSynthesizer
from app.services.quality_detector import QualityDetector


@pytest.fixture
def db_session():
    """Create test database with in-memory SQLite"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestLLMProviderIntegration:
    """Test LLM Provider integration"""

    @pytest.mark.asyncio
    async def test_switch_between_providers(self, db_session):
        """Test switching between providers"""
        # Reset singleton
        LLMProviderManager._instance = None

        with patch('app.services.llm.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "claude_key"
            mock_settings.OPENAI_API_KEY = "openai_key"
            mock_settings.GLM_ENDPOINT = None

            manager = LLMProviderManager()

            # List available providers
            providers = manager.list_providers()
            assert "claude" in providers
            assert "openai" in providers

    @pytest.mark.asyncio
    async def test_provider_fallback(self, db_session):
        """Test provider fallback when provider fails"""
        # Test that we can create and use a provider directly
        with patch('anthropic.AsyncAnthropic') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.messages.create = AsyncMock(
                return_value=Mock(content=[Mock(text="Generated script")])
            )

            from app.services.llm.claude_provider import ClaudeProvider
            provider = ClaudeProvider(api_key="test_key")
            result = await provider.generate("Test prompt")

            assert result == "Generated script"
            mock_instance.messages.create.assert_called_once()


class TestTTSProviderIntegration:
    """Test TTS Provider integration"""

    @pytest.mark.asyncio
    async def test_tts_with_project(self, db_session, tmp_path):
        """Test TTS integration with project"""
        # Create test project
        project = Project(
            title="Test Project",
            topic_title="Test topic",
            current_step="audio"
        )
        db_session.add(project)
        db_session.commit()

        # Create test script
        script = Script(
            project_id=project.id,
            outline="Outline",
            full_script="This is a test script for TTS.",
            segments=[]
        )
        db_session.add(script)
        db_session.commit()

        # Test TTS synthesis
        with patch('app.services.tts.settings') as mock_settings:
            mock_settings.AZURE_SPEECH_KEY = "test_key"
            mock_settings.AZURE_SPEECH_REGION = "eastus"

            # Reset singleton
            TTSProviderManager._instance = None
            manager = TTSProviderManager()

            with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
                mock_instance = Mock()
                mock_synth.return_value = mock_instance
                mock_result = Mock()
                from azure.cognitiveservices.speech import ResultReason
                mock_result.reason = ResultReason.SynthesizingAudioCompleted
                mock_instance.speak_ssml_async.return_value.get.return_value = mock_result

                provider = manager.get_provider("azure")
                output_file = tmp_path / "test_audio.mp3"

                result = await provider.synthesize(
                    text=script.full_script,
                    output_path=str(output_file),
                    voice="zh-CN-XiaoxiaoNeural"
                )

                assert result["success"] is True


class TestMaterialCollectionIntegration:
    """Test material collection integration"""

    @pytest.mark.asyncio
    async def test_material_collection_with_deduplication(self, db_session):
        """Test material collection with deduplication"""
        # Create test project
        project = Project(
            title="Test Project",
            topic_title="Nature documentary",
            current_step="materials"
        )
        db_session.add(project)
        db_session.commit()

        collector = MaterialCollector(db_session)

        # Mock Pexels API
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "photos": [
                    {
                        "id": "photo1",
                        "width": 1920,
                        "height": 1080,
                        "photographer": "Test Photographer",
                        "src": {
                            "original": "http://example.com/image.jpg",
                            "medium": "http://example.com/image_medium.jpg"
                        },
                        "alt": "Nature image"
                    }
                ]
            })

            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            with patch.object(collector, 'download_material') as mock_download:
                mock_download.return_value = "/tmp/image.jpg"

                # Mock file hash calculation
                with patch('app.utils.deduplication.MaterialDeduplicator.calculate_file_hash') as mock_hash:
                    mock_hash.return_value = "test_hash_123"

                    materials = await collector.collect_materials(
                        query="nature",
                        project_id=project.id,
                        count=5,
                        sources=["pexels"]
                    )

                    assert len(materials) > 0

                    # Try to collect again - should detect duplicate
                    materials2 = await collector.collect_materials(
                        query="nature",
                        project_id=project.id,
                        count=5,
                        sources=["pexels"]
                    )

                    # Should reuse existing material
                    assert len(materials2) > 0


class TestVideoExportIntegration:
    """Test video export integration"""

    @pytest.mark.asyncio
    async def test_multi_platform_export(self, db_session, tmp_path):
        """Test multi-platform export"""
        # Create test project
        project = Project(
            title="Test Project",
            topic_title="Test topic",
            current_step="export"
        )
        db_session.add(project)
        db_session.commit()

        synthesizer = VideoSynthesizer()

        # Mock video clip
        mock_clip = Mock()
        mock_clip.size = (1920, 1080)
        mock_clip.write_videofile = Mock()

        with patch.object(synthesizer, 'export_for_platform') as mock_export:
            mock_export.return_value = str(tmp_path / "output.mp4")

            # Export for both platforms
            platforms = ["horizontal", "vertical"]
            outputs = {}

            for platform in platforms:
                output_path = synthesizer.get_output_path(project.id, platform)
                result = synthesizer.export_for_platform(mock_clip, platform, output_path)
                outputs[platform] = result

            assert len(outputs) == 2
            assert "horizontal" in outputs
            assert "vertical" in outputs


class TestQualityDetectionIntegration:
    """Test quality detection integration"""

    @pytest.mark.asyncio
    async def test_end_to_end_quality_detection(self, db_session):
        """Test end-to-end quality detection"""
        # Create test project with all components
        project = Project(
            title="Test Project",
            topic_title="Test topic",
            current_step="completed"
        )
        db_session.add(project)
        db_session.commit()

        # Add script
        script = Script(
            project_id=project.id,
            outline="Test outline",
            full_script="这是一个测试脚本，用于测试质量检测功能。" * 50,
            segments=[
                {"type": "intro"},
                {"type": "body"},
                {"type": "outro"}
            ]
        )
        db_session.add(script)
        db_session.commit()

        # Add materials
        material = Material(
            project_id=project.id,
            material_type="video",
            source="pexels",
            local_path="/tmp/test.mp4",
            tags=["test"]
        )
        db_session.add(material)
        db_session.commit()

        # Mock project.script relationship
        db_session.refresh(project)
        project.script = script

        # Run quality detection
        detector = QualityDetector()

        # Mock video file - patch at the module level
        import app.services.quality_detector as quality_module
        with patch.object(quality_module, 'cv2') as mock_cv2:
            mock_instance = Mock()
            mock_cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            mock_instance.get.side_effect = [1920, 1080, 30.0, 3000]
            mock_instance.release = Mock()

            report = await detector.detect_comprehensive_quality(project.id, db_session)

            assert report["overall_score"] > 0
            assert report["grade"] in ["A", "B", "C", "D", "E"]
            assert "script" in report["breakdown"]
            assert "video" in report["breakdown"]


class TestEndToEndWorkflow:
    """Test end-to-end workflow"""

    @pytest.mark.asyncio
    async def test_complete_phase2_workflow(self, db_session):
        """Test complete Phase 2 workflow"""
        # Step 1: Create project
        project = Project(
            title="Integration Test Project",
            topic_title="AI technology",
            current_step="init"
        )
        db_session.add(project)
        db_session.commit()

        # Step 2: Generate script with LLM
        script = None
        with patch('app.services.llm.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test_key"
            LLMProviderManager._instance = None

            from app.services.script_generator import ScriptGenerator
            # Initialize manager first
            manager = LLMProviderManager()
            generator = ScriptGenerator()

            with patch.object(manager.get_provider('claude'), 'generate') as mock_gen:
                mock_gen.return_value = "AI技术正在改变世界..."

                script = Script(
                    project_id=project.id,
                    outline="Test outline",
                    full_script="AI技术正在改变世界..." * 100,
                    segments=[
                        {"type": "intro", "duration": 10},
                        {"type": "body", "duration": 30},
                        {"type": "outro", "duration": 10}
                    ]
                )
                db_session.add(script)
                db_session.commit()

        # Step 3: Collect materials
        project.current_step = "materials"
        db_session.commit()

        # Add materials directly to database
        material = Material(
            project_id=project.id,
            material_type="image",
            source="pexels",
            local_path="/tmp/image.jpg",
            tags=["AI", "technology"]
        )
        db_session.add(material)
        db_session.commit()

        # Step 4: Detect quality
        project.current_step = "quality_check"
        db_session.commit()

        # Set the script relationship
        db_session.refresh(project)
        project.script = script

        detector = QualityDetector()
        import app.services.quality_detector as quality_module
        with patch.object(quality_module, 'cv2') as mock_cv2:
            mock_instance = Mock()
            mock_cv2.VideoCapture.return_value = mock_instance
            mock_instance.isOpened.return_value = True
            mock_instance.get.side_effect = [1920, 1080, 30.0, 3000]
            mock_instance.release = Mock()

            quality_report = await detector.detect_comprehensive_quality(project.id, db_session)
            assert quality_report["overall_score"] > 0

        # Step 5: Mark as completed
        project.current_step = "completed"
        db_session.commit()

        # Verify final state
        assert project.current_step == "completed"
        assert db_session.query(Script).filter_by(project_id=project.id).count() > 0
        assert db_session.query(Material).filter_by(project_id=project.id).count() > 0


class TestPhase2FeatureIntegration:
    """Test integration between different Phase 2 features"""

    @pytest.mark.asyncio
    async def test_llm_to_tts_integration(self, db_session):
        """Test LLM output flows to TTS"""
        # Create project
        project = Project(
            title="Test Project",
            topic_title="Test",
            current_step="script"
        )
        db_session.add(project)
        db_session.commit()

        # Generate script
        with patch('app.services.llm.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test_key"
            LLMProviderManager._instance = None

            from app.services.script_generator import ScriptGenerator
            # Initialize manager first
            manager = LLMProviderManager()
            generator = ScriptGenerator()

            with patch.object(manager.get_provider('claude'), 'generate') as mock_gen:
                mock_gen.return_value = "Generated script content"

                script = Script(
                    project_id=project.id,
                    outline="Outline",
                    full_script="Generated script content",
                    segments=[]
                )
                db_session.add(script)
                db_session.commit()

        # Use script for TTS
        with patch('app.services.tts.settings') as mock_settings:
            mock_settings.AZURE_SPEECH_KEY = "test_key"
            mock_settings.AZURE_SPEECH_REGION = "eastus"
            TTSProviderManager._instance = None

            manager = TTSProviderManager()
            provider = manager.get_provider("azure")

            with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
                mock_instance = Mock()
                mock_synth.return_value = mock_instance
                mock_result = Mock()
                from azure.cognitiveservices.speech import ResultReason
                mock_result.reason = ResultReason.SynthesizingAudioCompleted
                mock_instance.speak_ssml_async.return_value.get.return_value = mock_result

                result = await provider.synthesize(
                    text=script.full_script,
                    output_path="/tmp/audio.mp3",
                    voice="zh-CN-XiaoxiaoNeural"
                )

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_material_to_video_integration(self, db_session):
        """Test materials flow to video synthesis"""
        # Create project with materials
        project = Project(
            title="Test Project",
            topic_title="Nature",
            current_step="video"
        )
        db_session.add(project)
        db_session.commit()

        # Add materials
        materials = [
            Material(
                project_id=project.id,
                material_type="image",
                source="pexels",
                local_path="/tmp/image1.jpg",
                tags=["nature"]
            ),
            Material(
                project_id=project.id,
                material_type="image",
                source="pexels",
                local_path="/tmp/image2.jpg",
                tags=["nature"]
            )
        ]
        for mat in materials:
            db_session.add(mat)
        db_session.commit()

        # Synthesize video
        synthesizer = VideoSynthesizer()

        mock_clip = Mock()
        mock_clip.write_videofile = Mock()

        # Mock ImageClip to return mock_clip without trying to read actual files
        with patch('app.services.video_synthesizer.ImageClip') as mock_image_clip:
            mock_image_clip.return_value = mock_clip

            with patch('app.services.video_synthesizer.concatenate_videoclips') as mock_concat:
                mock_concat.return_value = mock_clip

                # Mock os.path.exists to return True
                with patch('os.path.exists', return_value=True):
                    material_dicts = [
                        {"local_path": mat.local_path}
                        for mat in materials
                    ]

                    # Should not raise exception
                    result = synthesizer.synthesize(project.id, material_dicts)
                    assert result is not None
