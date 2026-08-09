import httpx
import base64
from typing import List, Optional

from app.providers.base import VoiceProvider, AudioResult, Voice
from app.config import settings


class ElevenLabsProvider(VoiceProvider):
    """ElevenLabs TTS provider"""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        emotion: Optional[str] = None,
    ) -> AudioResult:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.35,
                        "similarity_boost": 0.75,
                        "speed": speed,
                    },
                },
            )
            response.raise_for_status()
            audio_bytes = response.content
            audio_b64 = base64.b64encode(audio_bytes).decode()

            return AudioResult(
                audio_base64=f"data:audio/mp3;base64,{audio_b64}",
                duration_seconds=len(audio_bytes) / (128 * 1024 / 8),  # rough estimate
                format="mp3",
            )

    async def list_voices(self, language: Optional[str] = None) -> List[Voice]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key},
            )
            response.raise_for_status()
            data = response.json()

            voices = []
            for v in data.get("voices", []):
                voices.append(Voice(
                    id=v["voice_id"],
                    name=v["name"],
                    language=v.get("labels", {}).get("language", "en"),
                    accent=v.get("labels", {}).get("accent"),
                    gender=v.get("labels", {}).get("gender"),
                ))
            return voices


class MockVoiceProvider(VoiceProvider):
    """Mock voice provider for development."""

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        emotion: Optional[str] = None,
    ) -> AudioResult:
        return AudioResult(
            audio_base64="data:audio/mp3;base64,",
            duration_seconds=len(text.split()) * 0.5,
            format="mp3",
        )

    async def list_voices(self, language: Optional[str] = None) -> List[Voice]:
        return [
            Voice(id="mock-voice-1", name="Mock Voice", language="en", gender="female"),
            Voice(id="mock-voice-2", name="Mock Voice Male", language="en", gender="male"),
        ]
