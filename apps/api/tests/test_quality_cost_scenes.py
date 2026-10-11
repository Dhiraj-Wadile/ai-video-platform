import json
import importlib.util
import os
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, inspect, select, text

from app.database import async_session
from app.models.asset import Asset
from app.models.job import GenerationJob, RenderJob
from app.models.lineage import GenerationRecord
from app.models.project import Project
from app.models.quality import QualityReview
from app.models.script import Scene, Script
from app.providers.base import ImageResult, LLMProvider, LLMResponse
from app.services.render_service import RenderResult


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_token(client: AsyncClient, email: str = "qcs@example.com") -> str:
    await client.post("/api/auth/register", json={
        "email": email,
        "name": "QCS User",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def create_project(client: AsyncClient, token: str, name: str = "P") -> str:
    proj = await client.post("/api/projects", json={"name": name, "project_type": "short_form"},
                             headers=auth_headers(token))
    return proj.json()["id"]


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
    name = "pollinations"

    async def generate(self, prompt: str, size: str = "1080x1920", quality: str = "standard", n: int = 1):
        # The pipeline materialises every image on local disk before ffmpeg sees it, so the
        # fake must point at a file that actually exists.
        from app.services.storage_service import LocalStorage
        base = LocalStorage().base_dir
        key = "fake/generated.png"
        path = os.path.join(base, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nfake-image")
        return [ImageResult(url=f"/storage/{key}")]


class FakeRenderer:
    def __init__(self, config=None):
        pass

    async def render(self, scenes, output_path, background_music_path=None, music_volume=0.15,
                     captions=None, on_progress=None):
        import os
        import inspect
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"video-data")
        if on_progress:
            if inspect.iscoroutinefunction(on_progress):
                await on_progress(100, "done")
            else:
                on_progress(100, "done")
        return RenderResult(output_path=output_path, duration=sum(s.duration for s in scenes), file_size=11, format="mp4")


class FakeStorage:
    def __init__(self):
        self.writes = {}

    async def upload(self, data, key, content_type="application/octet-stream"):
        self.writes[key] = data
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
        from app.providers.base import ProviderTask
        self._map = {
            ProviderTask.LLM: SequenceOpenAI(),
            ProviderTask.IMAGE: FakePollinations(),
            ProviderTask.VOICE: FakeVoice(),
            ProviderTask.VIDEO: FakeVideo(),
        }

    def resolve_all(self):
        return dict(self._map)

    def resolve(self, task):
        from app.providers.base import ProviderTask
        if task == ProviderTask.IMAGE:
            return FakePollinations()
        return self._map[task]


@pytest.mark.anyio
async def test_quality_review_persists_and_marks_review(client: AsyncClient, monkeypatch):
    token = await get_token(client)
    pid = await create_project(client, token)

    async with async_session() as s:
        s.add(Script(project_id=pid, title="S", content="Some script content."))
        s.add(Scene(project_id=pid, scene_number=1, duration=3,
                    visual_description="Snowy mountain trail at dawn"))
        await s.commit()

    from app.api import projects as projects_api
    monkeypatch.setattr(projects_api, "QualityGate", FakeGate)

    resp = await client.post(f"/api/projects/{pid}/quality/review", json={}, headers=auth_headers(token))
    assert resp.status_code == 200
    review = resp.json()["review"]
    assert review["overall_score"] == 40
    assert review["passed"] is False
    assert review["problems"]

    async with async_session() as s:
        stored = (await s.execute(select(QualityReview).where(QualityReview.project_id == pid))).scalar_one_or_none()
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()

    assert stored is not None
    assert stored.overall_score == 40
    assert project.status == "review"


@pytest.mark.anyio
async def test_quality_review_passing_leaves_project(client: AsyncClient, monkeypatch):
    token = await get_token(client, email="pass@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        s.add(Script(project_id=pid, title="S", content="Some script content."))
        await s.commit()

    from app.api import projects as projects_api
    monkeypatch.setattr(projects_api, "QualityGate", PassingGate)

    resp = await client.post(f"/api/projects/{pid}/quality/review", json={}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["review"]["passed"] is True

    async with async_session() as s:
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    assert project.status != "review"


@pytest.mark.anyio
async def test_quality_endpoints_enforce_ownership(client: AsyncClient, monkeypatch):
    from app.api import projects as projects_api
    monkeypatch.setattr(projects_api, "QualityGate", PassingGate)

    token_a = await get_token(client, email="owner6@example.com")
    pid = await create_project(client, token_a)
    token_b = await get_token(client, email="other6@example.com")

    assert (await client.get(f"/api/projects/{pid}/quality", headers=auth_headers(token_b))).status_code == 404
    assert (await client.post(f"/api/projects/{pid}/quality/review", json={}, headers=auth_headers(token_b))).status_code == 404
    assert (await client.get(f"/api/projects/{pid}/costs", headers=auth_headers(token_b))).status_code == 404
    assert (await client.get(f"/api/projects/{pid}/lineage", headers=auth_headers(token_b))).status_code == 404


@pytest.mark.anyio
async def test_pipeline_persists_scene_assets_and_lineage(client: AsyncClient, monkeypatch):
    import app.services.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "provider_router", FakeRouter())
    monkeypatch.setattr(pipeline_mod, "VideoRenderer", FakeRenderer)
    monkeypatch.setattr(pipeline_mod, "get_storage", lambda: FakeStorage())

    token = await get_token(client, email="pipeline6@example.com")
    pid = await create_project(client, token)

    resp = await client.post("/api/render/start", json={
        "project_id": pid, "topic": "winter hiking", "duration": "30s", "style": "educational",
    }, headers=auth_headers(token))
    assert resp.status_code == 200

    async with async_session() as s:
        scene_assets = (await s.execute(
            select(Asset).where(Asset.project_id == pid, Asset.type == "scene_image")
        )).scalars().all()
        records = (await s.execute(
            select(GenerationRecord).where(GenerationRecord.project_id == pid)
        )).scalars().all()

    assert len(scene_assets) >= 1
    assert scene_assets[0].metadata_json["scene_id"] == 1

    by_task = [r.task for r in records]
    assert by_task.count("llm") == 2
    assert by_task.count("image") == len(scene_assets)
    assert "render" in by_task

    script_rec = next(r for r in records if r.task == "llm" and (r.context_json or {}).get("agent") == "script")
    storyboard_rec = next(r for r in records if r.task == "llm" and (r.context_json or {}).get("agent") == "storyboard")
    image_rec = next(r for r in records if r.task == "image")
    assert str(storyboard_rec.parent_id) == str(script_rec.id)
    assert str(image_rec.parent_id) == str(storyboard_rec.id)


@pytest.mark.anyio
async def test_project_costs_aggregates(client: AsyncClient):
    token = await get_token(client, email="cost@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        s.add(GenerationJob(project_id=pid, agent_name="script", status="completed", tokens_in=100, tokens_out=50, cost_cents=20, latency_ms=10))
        s.add(GenerationJob(project_id=pid, agent_name="storyboard", status="completed", tokens_in=0, tokens_out=0, cost_cents=30, latency_ms=20))
        s.add(GenerationRecord(project_id=pid, task="image", provider="pollinations", status="completed", cost_cents=5, latency_ms=100))
        await s.commit()

    resp = await client.get(f"/api/projects/{pid}/costs", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_cents"] == 55
    assert data["total_latency_ms"] == 130
    assert data["agent_breakdown"]["script"]["calls"] == 1
    assert data["task_breakdown"]["image"]["calls"] == 1


@pytest.mark.anyio
async def test_global_costs_is_user_scoped(client: AsyncClient):
    token_a = await get_token(client, email="a@example.com")
    token_b = await get_token(client, email="b@example.com")
    pid_a = await create_project(client, token_a)
    pid_b = await create_project(client, token_b)

    async with async_session() as s:
        s.add(GenerationJob(project_id=pid_a, agent_name="script", status="completed", cost_cents=77))
        s.add(GenerationJob(project_id=pid_b, agent_name="script", status="completed", cost_cents=11))
        await s.commit()

    resp_a = await client.get("/api/costs", headers=auth_headers(token_a))
    resp_b = await client.get("/api/costs", headers=auth_headers(token_b))
    assert resp_a.json()["totals"]["cost_cents"] == 77
    assert resp_b.json()["totals"]["cost_cents"] == 11


@pytest.mark.anyio
async def test_lineage_returns_parent_chain(client: AsyncClient):
    token = await get_token(client, email="lin@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        base = GenerationRecord(project_id=pid, task="llm", provider="openai", status="completed")
        s.add(base)
        await s.flush()
        s.add(GenerationRecord(project_id=pid, task="intelligence", provider="fake", status="completed", parent_id=str(base.id)))
        await s.commit()

    resp = await client.get(f"/api/projects/{pid}/lineage", headers=auth_headers(token))
    assert resp.status_code == 200
    records = resp.json()["records"]
    assert len(records) == 2
    child = next(r for r in records if r["task"] == "intelligence")
    assert child["parent_id"] == str(base.id)
    assert records == sorted(records, key=lambda r: r["created_at"] or "", reverse=True)


@pytest.mark.anyio
async def test_regenerate_scene_creates_asset_and_child_record(client: AsyncClient, monkeypatch):
    token = await get_token(client, email="regen@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        scene = Scene(project_id=pid, scene_number=2, duration=4,
                      visual_description="Desert at dusk", narration="n")
        s.add(scene)
        await s.flush()
        base = GenerationRecord(project_id=pid, task="image", provider="pollinations", status="completed",
                                context_json={"scene_id": 2})
        s.add(base)
        await s.commit()
        scene_id = str(scene.id)
        base_id = str(base.id)

    from app.api import projects as projects_api
    monkeypatch.setattr(projects_api, "provider_router", FakeRouter())

    resp = await client.post(f"/api/projects/{pid}/scenes/{scene_id}/regenerate", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["scene_number"] == 2
    assert data["parent_record_id"] == base_id
    assert data["asset_url"].startswith("/storage/")

    async with async_session() as s:
        assets = (await s.execute(
            select(Asset).where(Asset.project_id == pid, Asset.type == "scene_image")
        )).scalars().all()
        child = (await s.execute(
            select(GenerationRecord).where(GenerationRecord.parent_id == base_id)
        )).scalar_one_or_none()

    assert any(a.metadata_json.get("regenerated") for a in assets)
    assert child is not None
    assert child.context_json["scene_id"] == 2


@pytest.mark.anyio
async def test_recut_renders_from_persisted_scenes(client: AsyncClient, monkeypatch):
    token = await get_token(client, email="recut@example.com")
    pid = await create_project(client, token)

    async with async_session() as s:
        s.add(Script(project_id=pid, title="S", content="Words to read on screen."))
        s.add(Scene(project_id=pid, scene_number=1, duration=3,
                    visual_description="Snowy mountain", transition="fade"))
        s.add(Asset(project_id=pid, type="scene_image",
                    url="/storage/projects/x/scene/1.png",
                    metadata_json={"scene_id": 1}))
        await s.commit()

    from app.services import recut_service
    storage = FakeStorage()
    monkeypatch.setattr(recut_service, "VideoRenderer", FakeRenderer)
    monkeypatch.setattr(recut_service, "get_storage", lambda: storage)

    write_path = "storage/projects/x/scene/1.png"
    import os
    os.makedirs(os.path.dirname(write_path), exist_ok=True)
    with open(write_path, "wb") as f:
        f.write(b"fake-image")
    try:
        resp = await client.post("/api/render/recut", json={"project_id": pid},
                                 headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        job_id = resp.json()["job_id"]

        async with async_session() as s:
            job = (await s.execute(select(RenderJob).where(RenderJob.id == job_id))).scalar_one_or_none()
            videos = (await s.execute(
                select(Asset).where(Asset.project_id == pid, Asset.type == "video")
            )).scalars().all()

        assert job is not None
        assert job.status == "completed"
        assert job.output_url is not None
        assert len(videos) >= 1
        assert videos[0].metadata_json["source"] == "recut"
    finally:
        import shutil
        shutil.rmtree("storage", ignore_errors=True)
        shutil.rmtree("apps/api/storage", ignore_errors=True)


@pytest.mark.anyio
async def test_recut_rejects_foreign_project(client: AsyncClient):
    token_a = await get_token(client, email="owner3@example.com")
    pid = await create_project(client, token_a)
    token_b = await get_token(client, email="other3@example.com")

    resp = await client.post("/api/render/recut", json={"project_id": pid}, headers=auth_headers(token_b))
    assert resp.status_code == 404


class _FakeResult:
    def __init__(self, score=40, safe=True):
        self.structured_data = {
            "overall_score": score,
            "breakdown": {"hook_quality": score},
            "problems": [{"severity": "high", "description": "d", "suggestion": "s"}],
            "recommendations": ["r"],
            "safe_to_publish": safe,
        }


class _FakeAgent:
    async def run(self, input):
        return _FakeResult()


class FakeGate:
    # The endpoint now always passes llm_provider_name (a provider *name*, not an object),
    # so the fake has to accept it.
    def __init__(self, llm_provider_name=None):
        self.llm_provider_name = llm_provider_name

    async def review(self, project_id, script, scenes, db, source="manual"):
        from app.services.quality_service import _gate_passed
        review = QualityReview(
            project_id=project_id,
            overall_score=40,
            breakdown_json={"hook_quality": 40},
            problems_json=[{"severity": "high", "description": "hook weak"}],
            recommendations_json=["Improve the hook"],
            safe_to_publish=False,
            source=source,
        )
        db.add(review)
        await db.flush()
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not _gate_passed(review) and project is not None:
            project.status = "review"
        return review

    @staticmethod
    async def latest(db, project_id):
        return None


class PassingGate(FakeGate):
    async def review(self, project_id, script, scenes, db, source="manual"):
        from app.services.quality_service import _gate_passed
        review = QualityReview(
            project_id=project_id,
            overall_score=95,
            breakdown_json={},
            problems_json=[],
            recommendations_json=[],
            safe_to_publish=True,
            source=source,
        )
        db.add(review)
        await db.flush()
        return review

    @staticmethod
    async def latest(db, project_id):
        from app.models.quality import QualityReview
        return None


def test_migration_004_adds_and_drops_quality_and_lineage():
    module_path = str(Path(__file__).parent.parent / "migrations/versions/004_add_quality_and_lineage.py")
    spec = importlib.util.spec_from_file_location("migration_004", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    engine = create_engine("sqlite://")
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE projects (id VARCHAR(36) PRIMARY KEY)"))
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()

    inspector = inspect(engine)
    assert "quality_reviews" in inspector.get_table_names()
    assert "generation_records" in inspector.get_table_names()
    qr_cols = [c["name"] for c in inspector.get_columns("quality_reviews")]
    assert "overall_score" in qr_cols and "safe_to_publish" in qr_cols
    gr_cols = [c["name"] for c in inspector.get_columns("generation_records")]
    assert "parent_id" in gr_cols and "context_json" in gr_cols

    with engine.begin() as conn:
        module.op = Operations(MigrationContext.configure(conn))
        module.downgrade()

    inspector = inspect(engine)
    assert "quality_reviews" not in inspector.get_table_names()
    assert "generation_records" not in inspector.get_table_names()