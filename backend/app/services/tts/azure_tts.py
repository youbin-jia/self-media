# backend/app/services/tts/azure_tts.py
import azure.cognitiveservices.speech as speechsdk
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .base import BaseTTSProvider


class AzureTTSProvider(BaseTTSProvider):
    """Azure Speech TTS提供商"""

    def __init__(self, subscription_key: str, region: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.subscription_key = subscription_key
        self.region = region
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        # Thread pool for blocking Azure SDK calls
        self._executor = ThreadPoolExecutor(max_workers=3)

    @property
    def provider_name(self) -> str:
        return "azure"

    @property
    def available_models(self) -> List[str]:
        return ["azure-neural", "azure-standard"]

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        language: str = "zh-CN",
        speed: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """使用Azure TTS合成语音"""
        # 设置语音
        voice = voice or "zh-CN-XiaoxiaoNeural"
        self.speech_config.speech_synthesis_voice_name = voice

        # 设置输出格式
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )

        # 创建音频配置
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

        # 创建合成器
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        # 使用SSML控制语速
        ssml = f"""
        <speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="{language}">
            <voice name="{voice}">
                <prosody rate="{speed}">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

        # Run blocking Azure SDK call in thread pool executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: synthesizer.speak_ssml_async(ssml).get()
        )

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return {
                "success": True,
                "output_path": output_path,
                "duration": self.estimate_duration(text, speed),
                "voice": voice,
                "provider": self.provider_name
            }
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            raise RuntimeError(f"Azure TTS canceled: {cancellation_details.reason}")

        raise RuntimeError("Azure TTS synthesis failed")

    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出Azure可用声音"""
        # Azure预定义声音列表
        voices = {
            "zh-CN": [
                {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "Female"},
                {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "Male"},
                {"id": "zh-CN-YunyangNeural", "name": "云扬", "gender": "Male"},
                {"id": "zh-CN-XiaoyiNeural", "name": "晓伊", "gender": "Female"},
            ]
        }

        if language:
            return voices.get(language, [])
        return [
            {"language": lang, "voices": voice_list}
            for lang, voice_list in voices.items()
        ]
