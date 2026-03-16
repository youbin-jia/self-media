# backend/app/services/tts/elevenlabs_tts.py
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from .base import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs TTS提供商"""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    @property
    def available_models(self) -> List[str]:
        return ["eleven_multilingual_v2", "eleven_monolingual_v1"]

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        language: str = "zh-CN",
        speed: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """使用ElevenLabs TTS合成语音"""
        voice = voice or "21m00Tcm4TlvDq8ikWAM"  # Rachel (默认)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech/{voice}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                },
                timeout=60.0
            )

            if response.status_code != 200:
                # Sanitize error message to avoid exposing API keys
                error_msg = response.text
                # Remove common patterns that might contain API keys
                if "api_key" in error_msg.lower() or "authorization" in error_msg.lower():
                    error_msg = f"API error (status {response.status_code}): Authentication or authorization error"
                else:
                    # Truncate long error messages
                    error_msg = error_msg[:200] if len(error_msg) > 200 else error_msg
                raise RuntimeError(f"ElevenLabs API error: {error_msg}")

            # 保存音频文件
            Path(output_path).write_bytes(response.content)

            return {
                "success": True,
                "output_path": output_path,
                "duration": self.estimate_duration(text, speed),
                "voice": voice,
                "provider": self.provider_name
            }

    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出ElevenLabs可用声音"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key}
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return [
                {
                    "id": voice["voice_id"],
                    "name": voice["name"],
                    "labels": voice.get("labels", {})
                }
                for voice in data.get("voices", [])
            ]
