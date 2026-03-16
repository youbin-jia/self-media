# backend/tests/test_tts_providers.py
import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path
from app.services.tts.base import BaseTTSProvider
from app.services.tts.azure_tts import AzureTTSProvider
from app.services.tts.elevenlabs_tts import ElevenLabsTTSProvider
from app.services.tts import TTSProviderManager


class TestBaseTTSProvider:
    """测试TTS抽象基类"""

    def test_base_provider_is_abstract(self):
        """基类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseTTSProvider()

    def test_estimate_duration(self):
        """测试时长估算"""
        class ConcreteTTS(BaseTTSProvider):
            @property
            def provider_name(self):
                return "test"

            @property
            def available_models(self):
                return []

            async def synthesize(self, text, output_path, **kwargs):
                pass

            async def list_voices(self, **kwargs):
                return []

        provider = ConcreteTTS()
        # 中文约每秒3.5个字
        duration = provider.estimate_duration("这是测试文本", speed=1.0)
        assert 1.0 < duration < 2.0

        # 速度加倍，时长减半
        duration_fast = provider.estimate_duration("这是测试文本", speed=2.0)
        assert duration_fast < duration


class TestAzureTTSProvider:
    """测试Azure Speech TTS"""

    @pytest.mark.asyncio
    async def test_azure_synthesize_success(self, tmp_path):
        """测试Azure合成成功"""
        with patch('azure.cognitiveservices.speech.SpeechConfig') as mock_config:
            with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
                mock_instance = Mock()
                mock_synth.return_value = mock_instance

                # 模拟成功结果
                mock_result = Mock()
                mock_result.reason = Mock()
                from azure.cognitiveservices.speech import ResultReason
                mock_result.reason = ResultReason.SynthesizingAudioCompleted
                mock_instance.speak_ssml_async.return_value.get.return_value = mock_result

                provider = AzureTTSProvider(
                    subscription_key="test_key",
                    region="eastus"
                )

                output_file = tmp_path / "test.mp3"
                result = await provider.synthesize(
                    text="测试文本",
                    output_path=str(output_file),
                    voice="zh-CN-XiaoxiaoNeural"
                )

                assert result["success"] is True
                assert result["provider"] == "azure"
                assert "duration" in result

    @pytest.mark.asyncio
    async def test_azure_synthesize_canceled(self, tmp_path):
        """测试Azure合成取消"""
        with patch('azure.cognitiveservices.speech.SpeechConfig'):
            with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
                mock_instance = Mock()
                mock_synth.return_value = mock_instance

                # 模拟取消
                mock_result = Mock()
                mock_result.reason = Mock()
                from azure.cognitiveservices.speech import ResultReason
                mock_result.reason = ResultReason.Canceled
                mock_result.cancellation_details = Mock(reason="Cancelled")
                mock_instance.speak_ssml_async.return_value.get.return_value = mock_result

                provider = AzureTTSProvider(
                    subscription_key="test_key",
                    region="eastus"
                )

                with pytest.raises(RuntimeError, match="Azure TTS canceled"):
                    await provider.synthesize(
                        text="测试",
                        output_path=str(tmp_path / "test.mp3")
                    )

    @pytest.mark.asyncio
    async def test_azure_list_voices(self):
        """测试列出Azure声音"""
        provider = AzureTTSProvider(
            subscription_key="test_key",
            region="eastus"
        )

        voices = await provider.list_voices(language="zh-CN")
        assert len(voices) > 0
        assert any(v["id"] == "zh-CN-XiaoxiaoNeural" for v in voices)

    def test_azure_provider_name(self):
        """测试Azure provider名称"""
        provider = AzureTTSProvider(
            subscription_key="test_key",
            region="eastus"
        )
        assert provider.provider_name == "azure"


class TestElevenLabsTTSProvider:
    """测试ElevenLabs TTS"""

    @pytest.mark.asyncio
    async def test_elevenlabs_synthesize_success(self, tmp_path):
        """测试ElevenLabs合成成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake audio data"

        # Create an async context manager mock
        class AsyncContextManagerMock:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                return self.response

        mock_client_instance = AsyncContextManagerMock(mock_response)

        with patch('app.services.tts.elevenlabs_tts.httpx.AsyncClient', return_value=mock_client_instance):
            provider = ElevenLabsTTSProvider(api_key="test_key")
            output_file = tmp_path / "test.mp3"

            result = await provider.synthesize(
                text="Test text",
                output_path=str(output_file),
                voice="test_voice_id"
            )

            assert result["success"] is True
            assert result["provider"] == "elevenlabs"

    @pytest.mark.asyncio
    async def test_elevenlabs_synthesize_api_error(self, tmp_path):
        """测试ElevenLabs API错误"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        # Create an async context manager mock
        class AsyncContextManagerMock:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                return self.response

        mock_client_instance = AsyncContextManagerMock(mock_response)

        with patch('app.services.tts.elevenlabs_tts.httpx.AsyncClient', return_value=mock_client_instance):
            provider = ElevenLabsTTSProvider(api_key="test_key")

            with pytest.raises(RuntimeError, match="ElevenLabs API error"):
                await provider.synthesize(
                    text="Test",
                    output_path=str(tmp_path / "test.mp3")
                )

    @pytest.mark.asyncio
    async def test_elevenlabs_list_voices(self):
        """测试列出ElevenLabs声音"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "voices": [
                {"voice_id": "id1", "name": "Voice 1", "labels": {}},
                {"voice_id": "id2", "name": "Voice 2", "labels": {}}
            ]
        })

        # Create an async context manager mock
        class AsyncContextManagerMock:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, *args, **kwargs):
                return self.response

        mock_client_instance = AsyncContextManagerMock(mock_response)

        with patch('app.services.tts.elevenlabs_tts.httpx.AsyncClient', return_value=mock_client_instance):
            provider = ElevenLabsTTSProvider(api_key="test_key")
            voices = await provider.list_voices()

            assert len(voices) == 2
            assert voices[0]["id"] == "id1"


class TestTTSProviderManager:
    """测试TTS Provider管理器"""

    def test_manager_singleton(self):
        """测试管理器单例模式"""
        # Clear previous instance
        TTSProviderManager._instance = None

        manager1 = TTSProviderManager()
        manager2 = TTSProviderManager()
        assert manager1 is manager2

    @patch('app.services.tts.settings')
    def test_manager_initializes_configured_providers(self, mock_settings):
        """测试管理器初始化已配置的providers"""
        TTSProviderManager._instance = None

        mock_settings.AZURE_SPEECH_KEY = "test_key"
        mock_settings.AZURE_SPEECH_REGION = "eastus"
        mock_settings.ELEVENLABS_API_KEY = "elevenlabs_key"

        manager = TTSProviderManager()
        providers = manager.list_providers()

        assert "azure" in providers
        assert "elevenlabs" in providers

    def test_manager_get_provider(self):
        """测试获取provider"""
        TTSProviderManager._instance = None
        manager = TTSProviderManager()

        with pytest.raises(ValueError, match="not available"):
            manager.get_provider("nonexistent")


class TestAudioQualityDetection:
    """测试音频质量检测"""

    @pytest.mark.asyncio
    async def test_detect_audio_quality_success(self, tmp_path):
        """测试音频质量检测成功"""
        # Create a mock audio file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio" * 1000)

        with patch('librosa.load') as mock_load:
            import numpy as np
            # Mock audio data: 10 seconds at 22050 Hz
            mock_load.return_value = (np.random.rand(22050 * 10), 22050)

            from app.services.quality_detector import QualityDetector
            detector = QualityDetector()

            result = await detector.detect_audio_quality(str(audio_file))

            assert "overall_score" in result
            assert "grade" in result
            assert "metrics" in result
            assert result["grade"] in ["A", "B", "C", "D", "E"]
