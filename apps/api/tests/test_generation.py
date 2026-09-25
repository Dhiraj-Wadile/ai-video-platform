import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.asset import Asset
from app.models.job import GenerationJob, RenderJob
from app.models.project import Project
from app.models.script import Scene, Script
from app.providers.base import ImageResult, LLMProvider, LLMResponse
from app.services.render_service import RenderResult


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_token(client: AsyncClient, email: str = "gen@example.com") -> str:
    await client.post("/api/auth/register", json={
        "email": email,
        "name": "Gen User",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


SCRIPT_JSON = json.dumps({
    "title": "Winter Hiking",
    "duration": 30,
    "sections": {"hook": "H", "setup": "S", "conflict": "C", "payoff": "P", "cta": "CTA"},
    "full_script": "Winter hiking is amazing. Try it today.",
    "word_count": 8,
    "estimated_retention": "high",
})

STORYBOARD_JSON = json.dumps([{
    "scene_number": 1,
    "duration": 3,
    "character": None,
    "dialogue": None,
    "narration": "Winter hiking is amazing.",
    "visual_description": "Snowy mountain trail at dawn",
    "camera": "zoom_in",
    "emotion": "excitement",
    "background": "snowy mountains",
    "music_mood": "epic",
    "sfx": "wind",
    "caption": "Winter hiking",
    "transition": "fade",
}])


class SequenceOpenAI(LLMProvider):
    """Fake OpenAI provider that returns script JSON then storyboard JSON."""

    def __init__(self, responses=None):
        self._responses = responses or [SCRIPT_JSON, STORYBOARD_JSON]
        self._calls = 0

    async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, response_format=None):
        content = self._responses[min(self._calls, len(self._responses) - 1)]
        self._calls += 1
        return LLMResponse(content=content, model=model or "gpt-4o", tokens_in=10, tokens_out=12, latency_ms=5, cost_cents=0)

    async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
        yield ""


class FakePollinations:
    async def generate(self, prompt: str, size: str = "1080x1920", quality: str = "standard", n: int = 1):
        return [ImageResult(url="https://example.com/placeholder.png")]


class FakeRenderer:
    def __init__(self, config=None):
        pass

    async def render(self, scenes, output_path, background_music_path=None, music_volume=0.15, captions=None, on_progress=None):
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"video-data")
        if on_progress:
            import inspect
            if inspect.iscoroutinefunction(on_progress):
                await on_progress(100, "Render complete!")
            else:
                on_progress(100, "Render complete!")
        return RenderResult(output_path=output_path, duration=sum(s.duration for s in scenes), file_size=11, format="mp4")


class FakeStorage:
    async def upload(self, data, key, content_type="application/octet-stream"):
        return key

    async def get_url(self, key):
        return f"https://storage.example.com/{key}"


class FakeVoice:
    async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
        return None


class FakeVideo:
    async def generate(self, prompt, duration=5.0, image_url=None):
        return None


class FakeRouter:
    def __init__(self, llm, image, voice=None, video=None):
        from app.providers.base import ProviderTask
        self._map = {
            ProviderTask.LLM: llm,
            ProviderTask.IMAGE: image,
            ProviderTask.VOICE: voice or FakeVoice(),
            ProviderTask.VIDEO: video or FakeVideo(),
        }

    def resolve_all(self):
        return dict(self._map)


@pytest.mark.anyio
async def test_scripts_generate_persists_script(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.api.scripts.OpenAIProvider", SequenceOpenAI)
    token = await get_token(client)

    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token))
    pid = proj.json()["id"]

    resp = await client.post("/api/scripts/generate", json={
        "topic": "winter hiking",
        "duration": "30s",
        "project_id": pid,
    }, headers=auth_headers(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]
    assert data["title"] == "Winter Hiking"

    async with async_session() as s:
        script = (await s.execute(select(Script).where(Script.project_id == pid))).scalar_one_or_none()
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()

    assert script is not None
    assert script.title == "Winter Hiking"
    assert project.status == "generating"


@pytest.mark.anyio
async def test_scripts_generate_without_project_does_not_persist(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.api.scripts.OpenAIProvider", SequenceOpenAI)
    token = await get_token(client)

    resp = await client.post("/api/scripts/generate", json={"topic": "winter hiking"}, headers=auth_headers(token))

    assert resp.status_code == 200
    assert resp.json()["id"] is None


@pytest.mark.anyio
async def test_scripts_generate_rejects_foreign_project(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.api.scripts.OpenAIProvider", SequenceOpenAI)
    token_a = await get_token(client, email="owner@example.com")
    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token_a))
    pid = proj.json()["id"]

    token_b = await get_token(client, email="other@example.com")
    resp = await client.post("/api/scripts/generate", json={"topic": "x", "project_id": pid}, headers=auth_headers(token_b))

    assert resp.status_code == 404


@pytest.mark.anyio
async def test_render_start_persists_job_and_pipeline_outputs(client: AsyncClient, monkeypatch):
    import app.services.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "provider_router", FakeRouter(SequenceOpenAI(), FakePollinations()))
    monkeypatch.setattr(pipeline_mod, "VideoRenderer", FakeRenderer)
    monkeypatch.setattr(pipeline_mod, "get_storage", lambda: FakeStorage())

    token = await get_token(client)
    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token))
    pid = proj.json()["id"]

    resp = await client.post("/api/render/start", json={
        "project_id": pid,
        "topic": "winter hiking",
        "duration": "30s",
        "style": "educational",
    }, headers=auth_headers(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["job_id"]

    async with async_session() as s:
        job = (await s.execute(select(RenderJob).where(RenderJob.id == data["job_id"]))).scalar_one_or_none()
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        script = (await s.execute(select(Script).where(Script.project_id == pid))).scalar_one_or_none()
        scenes = (await s.execute(select(Scene).where(Scene.project_id == pid))).scalars().all()
        gen_jobs = (await s.execute(select(GenerationJob).where(GenerationJob.project_id == pid))).scalars().all()
        assets = (await s.execute(select(Asset).where(Asset.project_id == pid))).scalars().all()

    assert job is not None
    assert job.status == "completed"
    assert job.progress == 100
    assert job.output_url is not None

    assert project.status == "ready"
    assert script is not None
    assert script.title == "Winter Hiking"
    assert len(scenes) >= 1
    assert scenes[0].visual_description == "Snowy mountain trail at dawn"
    assert len(gen_jobs) == 2
    assert {j.agent_name for j in gen_jobs} == {"script", "storyboard"}
    assert {a.type for a in assets} == {"video", "captions"}
    assert any(a.type == "video" for a in assets)


@pytest.mark.anyio
async def test_render_start_marks_job_failed(client: AsyncClient, monkeypatch):
    from app.services.pipeline import PipelineResult

    class FailingPipeline:
        def __init__(self):
            pass

        async def run(self, project_id, topic, duration="30s", style="educational", db=None, on_progress=None):
            return PipelineResult(project_id=project_id, status="failed", error="boom")

    monkeypatch.setattr("app.api.render.VideoPipeline", FailingPipeline)

    token = await get_token(client)
    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token))
    pid = proj.json()["id"]

    resp = await client.post("/api/render/start", json={"project_id": pid, "topic": "x"},
                             headers=auth_headers(token))

    assert resp.status_code == 500

    async with async_session() as s:
        job = (await s.execute(select(RenderJob).where(RenderJob.project_id == pid))).scalar_one_or_none()

    assert job is not None
    assert job.status == "failed"
    assert job.error == "boom"


@pytest.mark.anyio
async def test_render_status_returns_persisted_job(client: AsyncClient, monkeypatch):
    from app.services.pipeline import PipelineResult

    class FakeVideoPipeline:
        def __init__(self):
            pass

        async def run(self, project_id, topic, duration="30s", style="educational", db=None, on_progress=None):
            return PipelineResult(project_id=project_id, status="completed", video_path="x.mp4")

    monkeypatch.setattr("app.api.render.VideoPipeline", FakeVideoPipeline)

    token = await get_token(client)
    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token))
    pid = proj.json()["id"]

    render_resp = await client.post("/api/render/start", json={"project_id": pid, "topic": "x"},
                                    headers=auth_headers(token))
    job_id = render_resp.json()["job_id"]

    status_resp = await client.get(f"/api/render/status/{job_id}", headers=auth_headers(token))

    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["progress"] == 100


@pytest.mark.anyio
async def test_render_start_rejects_foreign_project(client: AsyncClient, monkeypatch):
    token_a = await get_token(client, email="owner2@example.com")
    proj = await client.post("/api/projects", json={"name": "P", "project_type": "short_form"}, headers=auth_headers(token_a))
    pid = proj.json()["id"]

    token_b = await get_token(client, email="other2@example.com")
    resp = await client.post("/api/render/start", json={"project_id": pid, "topic": "x"}, headers=auth_headers(token_b))

    assert resp.status_code == 404