from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, AsyncIterator


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_cents: int


@dataclass
class ImageResult:
    url: str
    revised_prompt: Optional[str] = None


@dataclass
class AudioResult:
    audio_base64: str
    duration_seconds: float
    format: str = "mp3"


@dataclass
class VideoResult:
    url: str
    duration_seconds: float


@dataclass
class Voice:
    id: str
    name: str
    language: str
    accent: Optional[str] = None
    gender: Optional[str] = None
    preview_url: Optional[str] = None


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        pass


class ImageProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1792",
        quality: str = "standard",
        n: int = 1,
    ) -> List[ImageResult]:
        pass


class VoiceProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        emotion: Optional[str] = None,
    ) -> AudioResult:
        pass

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> List[Voice]:
        pass


class VideoProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        image_url: Optional[str] = None,
    ) -> VideoResult:
        pass


class MusicProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        mood: str,
        duration: float = 30.0,
        genre: Optional[str] = None,
    ) -> AudioResult:
        pass


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio_url: str,
        language: Optional[str] = None,
    ) -> dict:
        pass
