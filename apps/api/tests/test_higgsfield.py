import sys
import types

import pytest

from app.config import settings
from app.providers.base import ProviderTask
from app.providers.router import ProviderRouter
from app.providers.video import PollinationsVideoProvider, RunwayVideoProvider
from app.providers.video.higgsfield import HiggsfieldVideoProvider


def fake_higgsfield_module(result=None, subscribe_result=None, **kwargs):
    module = types.ModuleType("higgsfield_client")
    subscribe_result = subscribe_result if subscribe_result is not None else {}

    async def subscribe_async(model, arguments=None, **extra):
        subscribe_result["model"] = model
        subscribe_result["arguments"] = arguments or {}
        return result

    module.subscribe_async = subscribe_async
    return module


def test_video_resolves_higgsfield_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_api_key", "")
    assert isinstance(ProviderRouter().resolve(ProviderTask.VIDEO), PollinationsVideoProvider)

    monkeypatch.setattr(settings, "higgsfield_api_key", "hf-key")
    resolved = ProviderRouter().resolve(ProviderTask.VIDEO)
    assert isinstance(resolved, HiggsfieldVideoProvider)


def test_inventory_includes_higgsfield():
    infos = ProviderRouter().inventory()
    assert len(infos) == 7

    higgs = [i for i in infos if i.name == "higgsfield"][0]
    assert higgs.task == ProviderTask.VIDEO
    assert higgs.vendor == "higgsfield.ai"
    assert higgs.priority == 5
    assert higgs.is_mock is False


@pytest.mark.anyio
async def test_generate_submits_and_returns_video_url(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_api_key", "hf-key")
    monkeypatch.setattr(settings, "higgsfield_video_model", "higgsfield-ai/veo3.1")

    captured = {}
    module = fake_higgsfield_module(
        result={"status": "completed", "video": {"url": "https://cdn.higgsfield.ai/out.mp4"}},
        subscribe_result=captured,
    )
    monkeypatch.setitem(sys.modules, "higgsfield_client", module)

    provider = HiggsfieldVideoProvider()
    result = await provider.generate("A wave crashing")

    assert result.url == "https://cdn.higgsfield.ai/out.mp4"
    assert result.duration_seconds == 5.0
    assert captured["model"] == "higgsfield-ai/veo3.1"
    assert captured["arguments"] == {"prompt": "A wave crashing"}


@pytest.mark.anyio
async def test_generate_passes_image_url(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_video_model", "higgsfield-ai/veo3.1")

    captured = {}
    module = fake_higgsfield_module(
        result={"status": "completed", "video": {"url": "https://cdn/out.mp4"}},
        subscribe_result=captured,
    )
    monkeypatch.setitem(sys.modules, "higgsfield_client", module)

    provider = HiggsfieldVideoProvider()
    await provider.generate("Animate", duration=4.0, image_url="https://img.pollinations.ai/x.png")

    assert captured["arguments"] == {
        "prompt": "Animate",
        "image_url": "https://img.pollinations.ai/x.png",
    }


@pytest.mark.anyio
async def test_generate_failed_status_raises(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_video_model", "higgsfield-ai/veo3.1")

    module = fake_higgsfield_module(result={"status": "nsfw", "error": "blocked"})
    monkeypatch.setitem(sys.modules, "higgsfield_client", module)

    with pytest.raises(RuntimeError, match="nsfw"):
        await HiggsfieldVideoProvider().generate("bad")


@pytest.mark.anyio
async def test_generate_missing_sdk_raises_with_install_hint(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_video_model", "higgsfield-ai/veo3.1")
    monkeypatch.setitem(sys.modules, "higgsfield_client", None)

    with pytest.raises(RuntimeError, match="pip install higgsfield-client"):
        await HiggsfieldVideoProvider().generate("x")


@pytest.mark.anyio
async def test_generate_missing_model_setting_raises(monkeypatch):
    monkeypatch.setattr(settings, "higgsfield_video_model", "")

    module = fake_higgsfield_module(result={"status": "completed"})
    monkeypatch.setitem(sys.modules, "higgsfield_client", module)

    with pytest.raises(RuntimeError, match="HIGGSFIELD_VIDEO_MODEL"):
        await HiggsfieldVideoProvider().generate("x")