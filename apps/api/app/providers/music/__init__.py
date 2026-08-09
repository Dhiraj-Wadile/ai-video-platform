import httpx
from typing import Optional

from app.providers.base import MusicProvider, AudioResult


class PixabayMusicProvider(MusicProvider):
    """Free music generation/fetch via Pixabay API."""

    def __init__(self):
        self.base_url = "https://pixabay.com/api"

    async def generate(
        self,
        mood: str,
        duration: float = 30.0,
        genre: Optional[str] = None,
    ) -> AudioResult:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/music/",
                params={"q": f"{mood} {genre or ''}", "per_page": 1},
            )
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                if hits:
                    audio_url = hits[0].get("audio", "")
                    return AudioResult(
                        audio_base64=audio_url,
                        duration_seconds=duration,
                        format="mp3",
                    )

        return AudioResult(audio_base64="", duration_seconds=duration, format="mp3")


class FreeSoundMusicProvider(MusicProvider):
    """Music from FreeSound.org API."""

    def __init__(self):
        self.base_url = "https://freesound.org/apiv2"

    async def generate(
        self,
        mood: str,
        duration: float = 30.0,
        genre: Optional[str] = None,
    ) -> AudioResult:
        return AudioResult(audio_base64="", duration_seconds=duration, format="mp3")


class MockMusicProvider(MusicProvider):
    """Mock music provider for development."""

    async def generate(
        self,
        mood: str,
        duration: float = 30.0,
        genre: Optional[str] = None,
    ) -> AudioResult:
        return AudioResult(audio_base64="", duration_seconds=duration, format="mp3")
