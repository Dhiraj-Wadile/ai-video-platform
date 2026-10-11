from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, AsyncIterator


class ProviderTask(str, Enum):
    LLM = "llm"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    MUSIC = "music"
    TRANSCRIPTION = "transcription"


class ProviderNotConfigured(Exception):
    def __init__(self, task: ProviderTask, candidates: List[str]):
        self.task = task
        self.candidates = candidates
        super().__init__(
            f"No configured provider for task '{task.value}' "
            f"(candidates: {', '.join(candidates) or 'none'})"
        )


class ProviderRequestError(Exception):
    """A provider was reached but failed or returned nothing usable.

    Raised instead of returning a result object with an empty url: an empty url used to
    propagate into storage as a zero-byte file and a 200 response, which read as success.
    """

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"Provider '{provider}' failed: {message}")


@dataclass
class ProviderInfo:
    name: str
    task: ProviderTask
    vendor: str
    models: List[str]
    configured: bool
    enabled: bool
    is_mock: bool
    priority: int

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "task": self.task.value,
            "vendor": self.vendor,
            "models": self.models,
            "configured": self.configured,
            "enabled": self.enabled,
            "is_mock": self.is_mock,
            "priority": self.priority,
        }


class ProviderInfoMixin:
    name: str = "unknown"
    vendor: str = ""
    capability: Optional[ProviderTask] = None
    priority: int = 100
    is_mock: bool = False
    # ClassVar so subclasses cannot accidentally share one list between all providers.
    models: ClassVar[List[str]] = []

    @classmethod
    def is_configured(cls) -> bool:
        return True

    @classmethod
    def to_info(cls) -> ProviderInfo:
        return ProviderInfo(
            name=cls.name,
            task=cls.capability,
            vendor=cls.vendor,
            models=list(cls.models),
            configured=cls.is_configured(),
            enabled=cls.is_configured(),
            is_mock=cls.is_mock,
            priority=cls.priority,
        )


@dataclass
class GenerationResult:
    task: ProviderTask
    provider: str
    model: Optional[str] = None
    content: str = ""
    media_url: Optional[str] = None
    audio_base64: Optional[str] = None
    duration_seconds: Optional[float] = None
    format: Optional[str] = None
    latency_ms: int = 0
    cost_cents: int = 0
    usage: Dict[str, Any] = field(default_factory=dict)
    raw: Any = None

    def as_dict(self) -> dict:
        return {
            "task": self.task.value,
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "media_url": self.media_url,
            "duration_seconds": self.duration_seconds,
            "format": self.format,
            "latency_ms": self.latency_ms,
            "cost_cents": self.cost_cents,
            "usage": dict(self.usage),
        }


def adapt(
    result,
    task: ProviderTask,
    provider: str,
    model: Optional[str] = None,
) -> GenerationResult:
    if isinstance(result, LLMResponse):
        return GenerationResult(
            task=task,
            provider=provider,
            model=result.model or model,
            content=result.content,
            latency_ms=result.latency_ms,
            cost_cents=result.cost_cents,
            usage={"tokens_in": result.tokens_in, "tokens_out": result.tokens_out},
        )
    if isinstance(result, list) and result and isinstance(result[0], ImageResult):
        img = result[0]
        return GenerationResult(
            task=task,
            provider=provider,
            model=model,
            content=img.revised_prompt or "",
            media_url=img.url,
            format="image",
        )
    if isinstance(result, AudioResult):
        return GenerationResult(
            task=task,
            provider=provider,
            model=model,
            audio_base64=result.audio_base64,
            duration_seconds=result.duration_seconds,
            format=result.format,
        )
    if isinstance(result, VideoResult):
        return GenerationResult(
            task=task,
            provider=provider,
            model=model,
            media_url=result.url,
            duration_seconds=result.duration_seconds,
            format="video",
        )
    return GenerationResult(task=task, provider=provider, model=model, raw=result)


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
