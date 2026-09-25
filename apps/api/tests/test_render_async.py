import json
import importlib.util

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, inspect, select, text

from app.database import async_session
from app.models.job import RenderJob
from app.services.pipeline import PipelineResult


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_token(client: AsyncClient, email: str = "async@example.com") -> str:
    await client.post("/api/auth/register", json={
        "email": email,
        "name": "Async User",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


class FakeResult:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


async def create_project(client: AsyncClient, token: str, name: str = "P") -> str:
    proj = await client.post("/api/projects", json={"name": name, "project_type": "short_form"},
                             headers=auth_headers(token))
    return proj.json()["id"]


@pytest.mark.anyio
async def test_render_start_queues_job_when_async(client: AsyncClient, monkeypatch):
    from app.api import render as render_api

    captured = {}

    class FakeTask:
        def delay(self, **kwargs):
            captured.update(kwargs)
            return FakeResult(**kwargs)

    monkeypatch.setattr(render_api.settings, "render_async", True)
    monkeypatch.setattr(render_api, "render_project", FakeTask())

    token = await get_token(client)
    pid = await create_project(client, token)

    resp = await client.post("/api/render/start", json={
        "project_id": pid,
        "topic": "winter hiking",
        "duration": "30s",
        "style": "educational",
    }, headers=auth_headers(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"]
    assert data["message"] == "Render queued"

    assert captured["project_id"] == pid
    assert captured["topic"] == "winter hiking"
    assert captured["duration"] == "30s"
    assert captured["style"] == "educational"


@pytest.mark.anyio
async def test_render_start_enqueue_failure_marks_job_failed(client: AsyncClient, monkeypatch):
    from app.api import render as render_api

    class FailingTask:
        def delay(self, **kwargs):
            raise RuntimeError("broker unreachable")

    monkeypatch.setattr(render_api.settings, "render_async", True)
    monkeypatch.setattr(render_api, "render_project", FailingTask())

    token = await get_token(client)
    pid = await create_project(client, token)

    resp = await client.post("/api/render/start", json={"project_id": pid, "topic": "x"},
                             headers=auth_headers(token))

    assert resp.status_code == 500

    async with async_session() as s:
        job = (await s.execute(
            select(RenderJob).where(RenderJob.project_id == pid)
        )).scalar_one_or_none()

    assert job is not None
    assert job.status == "failed"
    assert "Failed to enqueue render" in job.error


@pytest.mark.anyio
async def test_render_project_task_runs_pipeline(client: AsyncClient, monkeypatch):
    import app.services.pipeline as pipeline_mod
    from app.providers.base import LLMProvider, LLMResponse, ImageResult, ProviderTask

    SCRIPT_JSON = json.dumps({
        "title": "Winter Hiking",
        "duration": 30,
        "sections": {"hook": "H"},
        "full_script": "Winter hiking is amazing. Try it today.",
    })
    STORYBOARD_JSON = json.dumps([{
        "scene_number": 1,
        "duration": 3,
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
        def __init__(self):
            self._responses = [SCRIPT_JSON, STORYBOARD_JSON]
            self._calls = 0

        async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, response_format=None):
            content = self._responses[min(self._calls, len(self._responses) - 1)]
            self._calls += 1
            return LLMResponse(content=content, model="gpt-4o", tokens_in=5, tokens_out=5, latency_ms=5, cost_cents=0)

        async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
            yield ""

    class FakePollinations:
        async def generate(self, prompt, size="1080x1920", quality="standard", n=1):
            return [ImageResult(url="https://example.com/placeholder.png")]

    class FakeRenderer:
        def __init__(self, config=None):
            pass

        async def render(self, scenes, output_path, background_music_path=None, music_volume=0.15,
                         captions=None, on_progress=None):
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"video-data")
            if on_progress:
                await on_progress(100, "Render complete!")
            from app.services.render_service import RenderResult
            return RenderResult(output_path=output_path, duration=sum(s.duration for s in scenes),
                                file_size=11, format="mp4")

    class FakeStorage:
        async def upload(self, data, key, content_type="application/octet-stream"):
            return key

        async def get_url(self, key):
            return f"https://storage.example.com/{key}"

    class FakeVoice:
        async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
            return None
        async def list_voices(self, language=None):
            return []

    class FakeVideo:
        async def generate(self, prompt, duration=5.0, image_url=None):
            return None

    class FakeRouter:
        def __init__(self):
            self._map = {
                ProviderTask.LLM: SequenceOpenAI(),
                ProviderTask.IMAGE: FakePollinations(),
                ProviderTask.VOICE: FakeVoice(),
                ProviderTask.VIDEO: FakeVideo(),
            }

        def resolve_all(self):
            return dict(self._map)

    monkeypatch.setattr(pipeline_mod, "provider_router", FakeRouter())
    monkeypatch.setattr(pipeline_mod, "VideoRenderer", FakeRenderer)
    monkeypatch.setattr(pipeline_mod, "get_storage", lambda: FakeStorage())

    from app.tasks.render_tasks import render_project

    token = await get_token(client)
    pid = await create_project(client, token)

    async with async_session() as s:
        job = RenderJob(project_id=pid, status="queued", progress=0)
        s.add(job)
        await s.commit()
        job_id = str(job.id)

    result = render_project(job_id=job_id, project_id=pid, topic="winter hiking",
                            duration="30s", style="educational")

    assert result["status"] == "completed"

    async with async_session() as s:
        job = (await s.execute(select(RenderJob).where(RenderJob.id == job_id))).scalar_one_or_none()
        from app.models.project import Project
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()

    assert job.status == "completed"
    assert job.progress == 100
    assert job.progress_message is not None
    assert job.output_url is not None
    assert job.completed_at is not None
    assert project.status == "ready"


@pytest.mark.anyio
async def test_render_project_task_marks_failed(client: AsyncClient, monkeypatch):
    from app.tasks.render_tasks import render_project

    class FailingPipeline:
        def __init__(self):
            pass

        async def run(self, project_id, topic, duration="30s", style="educational", db=None, on_progress=None):
            return PipelineResult(project_id=project_id, status="failed", error="boom")

    monkeypatch.setattr("app.tasks.render_tasks.VideoPipeline", FailingPipeline)

    token = await get_token(client, email="fail@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        job = RenderJob(project_id=pid, status="queued", progress=0)
        s.add(job)
        await s.commit()
        job_id = str(job.id)

    result = render_project(job_id=job_id, project_id=pid, topic="x", duration="30s", style="x")

    assert result["status"] == "failed"

    async with async_session() as s:
        job = (await s.execute(select(RenderJob).where(RenderJob.id == job_id))).scalar_one_or_none()

    assert job.status == "failed"
    assert job.error == "boom"


@pytest.mark.anyio
async def test_render_status_includes_progress_message(client: AsyncClient, monkeypatch):
    from app.services.pipeline import PipelineResult

    class FakeVideoPipeline:
        def __init__(self):
            pass

        async def run(self, project_id, topic, duration="30s", style="educational", db=None, on_progress=None):
            if on_progress:
                on_progress(50, "Generating scene visuals...")
                on_progress(100, "Pipeline complete!")
            return PipelineResult(project_id=project_id, status="completed", video_path="x.mp4")

    monkeypatch.setattr("app.api.render.VideoPipeline", FakeVideoPipeline)

    token = await get_token(client, email="status@example.com")
    pid = await create_project(client, token)

    resp = await client.post("/api/render/start", json={"project_id": pid, "topic": "x"},
                             headers=auth_headers(token))
    job_id = resp.json()["job_id"]

    status_resp = await client.get(f"/api/render/status/{job_id}", headers=auth_headers(token))

    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["progress_message"] == "Pipeline complete!"
    assert "error" in data


def test_migration_003_adds_and_drops_progress_message():
    from pathlib import Path
    module_path = str(Path(__file__).parent.parent / "migrations/versions/003_add_render_job_progress_message.py")
    spec = importlib.util.spec_from_file_location("migration_003", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = create_engine("sqlite://")
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE render_jobs (id VARCHAR(36) PRIMARY KEY, project_id VARCHAR(36) NOT NULL, "
            "status VARCHAR(20))"
        ))
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()

    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("render_jobs")]
    assert "progress_message" in columns

    with engine.begin() as conn:
        module.op = Operations(MigrationContext.configure(conn))
        module.downgrade()

    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("render_jobs")]
    assert "progress_message" not in columns