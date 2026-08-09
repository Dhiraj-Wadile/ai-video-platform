import httpx
from typing import Optional

from app.providers.base import TranscriptionProvider
from app.config import settings


class WhisperTranscriptionProvider(TranscriptionProvider):
    """OpenAI Whisper API transcription provider."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"

    async def transcribe(
        self,
        audio_url: str,
        language: Optional[str] = None,
    ) -> dict:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured for transcription")

        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()

            files = {"file": ("audio.mp3", audio_resp.content, "audio/mpeg")}
            data = {"model": "whisper-1"}
            if language:
                data["language"] = language

            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            return {"text": result.get("text", ""), "language": language}


class MockTranscriptionProvider(TranscriptionProvider):
    """Mock transcription for development."""

    async def transcribe(
        self,
        audio_url: str,
        language: Optional[str] = None,
    ) -> dict:
        return {"text": "Mock transcription placeholder", "language": language}
