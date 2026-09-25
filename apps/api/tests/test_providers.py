import pytest
from httpx import AsyncClient

from app.config import settings
from app.providers.base import (
    ProviderTask,
    ProviderNotConfigured,
    LLMResponse,
    ImageResult,
    AudioResult,
    VideoResult,
    adapt,
)
from app.providers.llm.openai import OpenAIProvider
from app.providers.image.providers import PollinationsProvider
from app.providers.voice.providers import ElevenLabsProvider, MockVoiceProvider
from app.providers.video import RunwayVideoProvider, PollinationsVideoProvider
from app.providers.router import ProviderRouter, PROVIDER_REGISTRY


def test_resolve_prefers_configured_real_over_mock(monkeypatch):
    monkeypatch.setattr(settings, "elevenlabs_api_key", "")
    router = ProviderRouter()
    resolved = router.resolve(ProviderTask.VOICE)
    assert isinstance(resolved, MockVoiceProvider)

    monkeypatch.setattr(settings, "elevenlabs_api_key", "sk-test")
    resolved = router.resolve(ProviderTask.VOICE)
    assert isinstance(resolved, ElevenLabsProvider)


def test_resolve_video_prefers_runway_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "runway_api_key", "")
    assert isinstance(router_resolve_video(), PollinationsVideoProvider)

    monkeypatch.setattr(settings, "runway_api_key", "rw-test")
    assert isinstance(router_resolve_video(), RunwayVideoProvider)


def router_resolve_video():
    return ProviderRouter().resolve(ProviderTask.VIDEO)


def test_resolve_llm_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(ProviderNotConfigured) as exc_info:
        ProviderRouter().resolve(ProviderTask.LLM)
    assert exc_info.value.task == ProviderTask.LLM
    assert "openai" in exc_info.value.candidates


def test_resolve_by_name_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(ProviderNotConfigured):
        ProviderRouter().resolve(ProviderTask.LLM, name="openai")


def test_resolve_image_when_llm_locked_out(monkeypatch):
    monkeypatch.setattr(settings, "runway_api_key", "x")
    monkeypatch.setattr(settings, "elevenlabs_api_key", "y")
    monkeypatch.setattr(settings, "openai_api_key", "")
    router = ProviderRouter()
    assert isinstance(router.resolve(ProviderTask.IMAGE), PollinationsProvider)
    assert isinstance(router.resolve(ProviderTask.VOICE), ElevenLabsProvider)


def test_inventory_includes_seven_providers():
    router = ProviderRouter()
    infos = router.inventory()
    assert len(infos) == 7

    by_name = {(i.task, i.name): i for i in infos}
    assert by_name[(ProviderTask.LLM, "openai")].configured is bool(settings.openai_api_key)
    assert by_name[(ProviderTask.IMAGE, "pollinations")].configured is True
    assert by_name[(ProviderTask.VOICE, "mock-voice")].is_mock is True
    assert by_name[(ProviderTask.VIDEO, "runway")].configured is bool(settings.runway_api_key)
    assert by_name[(ProviderTask.VIDEO, "pollinations")].vendor == "pollinations.ai"
    assert by_name[(ProviderTask.VIDEO, "higgsfield")].priority == 5

    dicts = router.as_dicts()
    first = dicts[0]
    assert first["task"] in {t.value for t in ProviderTask}
    assert set(first.keys()) >= {
        "name", "task", "vendor", "models", "configured", "enabled", "is_mock", "priority",
    }


def test_resolve_all_returns_four_tasks(monkeypatch):
    from app.providers.router import PROVIDER_REGISTRY

    monkeypatch.setattr(settings, "elevenlabs_api_key", "")
    monkeypatch.setattr(settings, "runway_api_key", "")

    class MockLLMForTest:
        name = "mock-llm"
        default_model = "mock-model"
        is_mock = True
        priority = 100

        @classmethod
        def is_configured(cls):
            return True

    # resolve() applies the same policy to every task; give LLM a mock so the
    # full resolve_all() succeeds even with no OpenAI key configured.
    monkeypatch.setitem(PROVIDER_REGISTRY, ProviderTask.LLM, [MockLLMForTest])

    resolved = ProviderRouter().resolve_all()
    assert set(resolved.keys()) == {
        ProviderTask.LLM, ProviderTask.IMAGE, ProviderTask.VOICE, ProviderTask.VIDEO,
    }
    assert isinstance(resolved[ProviderTask.VOICE], MockVoiceProvider)
    assert isinstance(resolved[ProviderTask.VIDEO], PollinationsVideoProvider)


def test_adapt_llm():
    result = adapt(
        LLMResponse(content="hi", model="gpt-4o", tokens_in=5, tokens_out=7, latency_ms=3, cost_cents=1),
        ProviderTask.LLM,
        "openai",
    )
    assert result.content == "hi"
    assert result.model == "gpt-4o"
    assert result.usage == {"tokens_in": 5, "tokens_out": 7}
    assert result.task == ProviderTask.LLM
    assert result.provider == "openai"


def test_adapt_image():
    result = adapt([ImageResult(url="https://img", revised_prompt="prompt")], ProviderTask.IMAGE, "pollinations")
    assert result.media_url == "https://img"
    assert result.content == "prompt"
    assert result.format == "image"


def test_adapt_audio():
    result = adapt(AudioResult(audio_base64="data", duration_seconds=2.5), ProviderTask.VOICE, "elevenlabs")
    assert result.audio_base64 == "data"
    assert result.duration_seconds == 2.5
    assert result.format == "mp3"


def test_adapt_video():
    result = adapt(VideoResult(url="https://vid", duration_seconds=5.0), ProviderTask.VIDEO, "runway")
    assert result.media_url == "https://vid"
    assert result.duration_seconds == 5.0
    assert result.format == "video"


@pytest.mark.anyio
async def test_providers_endpoint_returns_inventory(client: AsyncClient):
    resp = await client.get("/api/providers")
    assert resp.status_code in (401, 403)

    await client.post("/api/auth/register", json={
        "email": "providers@example.com",
        "name": "Provider User",
        "password": "testpass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": "providers@example.com",
        "password": "testpass123",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/providers", headers=headers)
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    assert len(providers) == 7
    names = {p["name"] for p in providers}
    assert {"openai", "pollinations", "elevenlabs", "mock-voice", "runway", "higgsfield"} <= names


@pytest.mark.anyio
async def test_pipeline_uses_router_and_records_selection(client: AsyncClient, monkeypatch):
    from app.providers.router import PROVIDER_REGISTRY, provider_router

    class FakeLLM:
        name = "fake-llm"
        default_model = "fake-model"
        is_mock = False
        priority = 10

        @classmethod
        def is_configured(cls):
            return True

        async def complete(self, *args, **kwargs):
            raiser = Exception("should not be called")
            raise raiser

    monkeypatch.setitem(PROVIDER_REGISTRY, ProviderTask.LLM, [FakeLLM])

    from app.services.pipeline import VideoPipeline

    pipeline = VideoPipeline()
    selection = pipeline.providers_metadata
    assert set(selection.keys()) == {"llm", "image", "voice", "video"}
    assert all("name" in v for v in selection.values())
    assert selection["llm"] == {"name": "fake-llm", "model": "fake-model"}
    assert isinstance(pipeline.llm, FakeLLM)