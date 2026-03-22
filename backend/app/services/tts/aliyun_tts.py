from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import urlencode
import time
import threading
import json
import logging
import re
import httpx

from .base import BaseTTSProvider

logger = logging.getLogger(__name__)


class AliyunTTSProvider(BaseTTSProvider):
    """Aliyun NLS TTS provider via gateway HTTP API."""

    def __init__(
        self,
        token: Optional[str],
        app_key: str,
        region: str = "cn-shanghai",
        voice: str = "xiaoyun",
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(config)
        self.token = token
        self.app_key = app_key
        self.region = region
        self.default_voice = voice
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.gateway = f"https://nls-gateway-{region}.aliyuncs.com/stream/v1/tts"
        self._token_expire_ts = 0.0
        self._token_lock = threading.Lock()
        self._last_refresh_ts = 0.0

    @property
    def provider_name(self) -> str:
        return "aliyun"

    @property
    def available_models(self) -> List[str]:
        return ["aliyun-nls-stream-tts"]

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        language: str = "zh-CN",
        speed: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Synthesize speech with Aliyun NLS TTS gateway."""
        _ = language  # Keep interface compatibility.
        if not text or not str(text).strip():
            raise RuntimeError("Aliyun TTS text is empty")

        selected_voice = voice or self.default_voice
        # Map speed(0.5~2.0) to Aliyun speech_rate(-500~500), keep conservative range.
        speech_rate = int(max(-450, min(450, (speed - 1.0) * 300)))
        format_name = str(kwargs.get("format", "mp3")).lower()
        sample_rate = int(kwargs.get("sample_rate", 16000))
        pitch_rate = int(kwargs.get("pitch_rate", 0))
        volume = int(kwargs.get("volume", 50))

        token = self._get_valid_token()
        params = {
            "appkey": self.app_key,
            "token": token,
            "text": text,
            "format": format_name,
            "sample_rate": sample_rate,
            "voice": selected_voice,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate,
            "volume": volume
        }
        request_url = f"{self.gateway}?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(request_url)

        content_type = (response.headers.get("content-type") or "").lower()
        # Token can expire during runtime; refresh once and retry.
        if response.status_code in (400, 401, 403) and self.access_key_id and self.access_key_secret:
            if "token" in (response.text or "").lower():
                self._refresh_token(force=True)
                params["token"] = self.token
                request_url = f"{self.gateway}?{urlencode(params)}"
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(request_url)
                content_type = (response.headers.get("content-type") or "").lower()

        if response.status_code != 200 or "audio" not in content_type:
            detail = self._sanitize_message(response.text[:300] if response.text else f"status={response.status_code}")
            raise RuntimeError(f"Aliyun TTS API error: {detail}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)

        return {
            "success": True,
            "output_path": str(output),
            "duration": self.estimate_duration(text, speed),
            "voice": selected_voice,
            "provider": self.provider_name,
            "sample_rate": sample_rate,
            "format": format_name
        }

    def _get_valid_token(self) -> str:
        if self.token and time.time() < (self._token_expire_ts - 60):
            return self.token
        if self.token and self._token_expire_ts == 0 and not (self.access_key_id and self.access_key_secret):
            # Static token mode without refresh credentials.
            return self.token
        logger.info(
            "[AliyunTTS] token refresh needed; has_ak=%s has_static_token=%s",
            bool(self.access_key_id and self.access_key_secret),
            bool(self.token)
        )
        self._refresh_token(force=False)
        if not self.token:
            raise RuntimeError("Aliyun TTS token unavailable, please configure token or AccessKey credentials")
        return self.token

    def _refresh_token(self, force: bool = False) -> None:
        if not (self.access_key_id and self.access_key_secret):
            return
        with self._token_lock:
            if not force and self.token and time.time() < (self._token_expire_ts - 60):
                return

            try:
                from aliyunsdkcore.client import AcsClient
                from aliyunsdkcore.request import CommonRequest
            except Exception as exc:
                raise RuntimeError(
                    "Missing dependency aliyun-python-sdk-core; install it for auto token refresh"
                ) from exc

            client = AcsClient(self.access_key_id, self.access_key_secret, self.region)
            request = CommonRequest()
            request.set_accept_format("json")
            request.set_domain(f"nls-meta.{self.region}.aliyuncs.com")
            request.set_version("2019-02-28")
            request.set_action_name("CreateToken")
            request.set_method("POST")

            try:
                response_bytes = client.do_action_with_exception(request)
                payload = response_bytes.decode("utf-8")
                data = json.loads(payload)
            except Exception as exc:
                logger.exception("[AliyunTTS] CreateToken failed: %s", self._sanitize_message(str(exc)))
                raise RuntimeError("Aliyun CreateToken failed, check AccessKey credentials and region") from exc
            token_info = ((data or {}).get("Token") or {})
            token = token_info.get("Id")
            expire_time = float(token_info.get("ExpireTime") or 0)
            if not token:
                logger.error("[AliyunTTS] CreateToken returned invalid payload: %s", self._sanitize_message(payload[:300]))
                raise RuntimeError("Aliyun CreateToken failed: no token in response")
            self.token = token
            self._token_expire_ts = expire_time if expire_time > 0 else (time.time() + 1800)
            self._last_refresh_ts = time.time()
            logger.info(
                "[AliyunTTS] token refreshed; region=%s app_key=%s expires_at=%s",
                self.region,
                self._mask_value(self.app_key),
                int(self._token_expire_ts)
            )

    def _mask_value(self, value: Optional[str], keep: int = 4) -> str:
        if not value:
            return ""
        text = str(value)
        if len(text) <= keep * 2:
            return "*" * len(text)
        return f"{text[:keep]}***{text[-keep:]}"

    def _sanitize_message(self, message: str) -> str:
        if not message:
            return ""
        sanitized = str(message)
        for secret in [self.token, self.access_key_id, self.access_key_secret, self.app_key]:
            if secret:
                sanitized = sanitized.replace(secret, "[REDACTED]")
        sanitized = re.sub(r"(?i)(access[-_ ]?key[^=:]*[=:]\s*)([A-Za-z0-9+/=_-]+)", r"\1[REDACTED]", sanitized)
        sanitized = re.sub(r"(?i)(token[^=:]*[=:]\s*)([A-Za-z0-9+/=_-]+)", r"\1[REDACTED]", sanitized)
        return sanitized

    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return common Aliyun Chinese voices (static list)."""
        voices = [
            {"id": "xiaoyun", "name": "小云", "gender": "Female", "language": "zh-CN"},
            {"id": "xiaogang", "name": "小刚", "gender": "Male", "language": "zh-CN"},
            {"id": "ruoxi", "name": "若兮", "gender": "Female", "language": "zh-CN"},
            {"id": "siqi", "name": "思琪", "gender": "Female", "language": "zh-CN"},
            {"id": "sijia", "name": "思佳", "gender": "Female", "language": "zh-CN"},
            {"id": "aida", "name": "艾达", "gender": "Female", "language": "zh-CN"}
        ]
        if language:
            return [v for v in voices if v.get("language") == language]
        return voices
