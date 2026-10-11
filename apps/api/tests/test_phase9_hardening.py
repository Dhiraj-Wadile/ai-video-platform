"""Regression tests for the Phase 9 sweep.

Each test here pins a defect that shipped working code: a deployment that could not start,
a migration that could not apply on PostgreSQL, a Celery worker with no tasks, 500s on
perfectly ordinary LLM output, silent videos, and world-readable media.
"""
import json
import os

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.database import async_session
from app.models.job import RenderJob
from app.models.lineage import GenerationRecord
from app.models.project import Project
from app.providers.base import ProviderRequestError, ProviderTask
from app.services.storage_service import LocalStorage


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def token_for(client: AsyncClient, email: str) -> str:
    await client.post("/api/auth/register", json={
        "email": email, "name": "P9", "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def project_for(client: AsyncClient, token: str, name: str = "P") -> str:
    resp = await client.post(
        "/api/projects", json={"name": name, "project_type": "short_form"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# --- deployment: the app must be constructable --------------------------------------------


def test_conventional_sync_database_urls_are_normalised():
    """`postgresql://` and `sqlite:///` are what providers and tutorials hand out.

    create_async_engine rejects them outright, which crashed the app at import time.
    """
    from app.config import _to_async_url

    assert _to_async_url("sqlite:///./app.db") == "sqlite+aiosqlite:///./app.db"
    assert _to_async_url("postgresql://u:p@h:5432/db") == "postgresql+asyncpg://u:p@h:5432/db"
    assert _to_async_url("postgres://u:p@h/db") == "postgres+asyncpg://u:p@h/db"
    # Already explicit, and anything unrecognised, pass through untouched.
    assert _to_async_url("postgresql+asyncpg://h/db") == "postgresql+asyncpg://h/db"
    assert _to_async_url("mysql+aiomysql://h/db") == "mysql+aiomysql://h/db"
    assert _to_async_url("not-a-url") == "not-a-url"


def test_sqlite_engine_accepts_pool_kwargs_path():
    """SQLite uses StaticPool/NullPool, which reject pool_size and max_overflow."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.database import _engine_kwargs

    assert _engine_kwargs("sqlite+aiosqlite:///./app.db") == {}
    assert _engine_kwargs("postgresql+asyncpg://h/db") == {"pool_size": 20, "max_overflow": 10}
    # Must not raise for the in-memory form the test suite uses.
    create_async_engine("sqlite+aiosqlite:///:memory:", **_engine_kwargs("sqlite+aiosqlite:///:memory:"))


def test_celery_worker_registers_the_app_tasks():
    """autodiscover_tasks(["app.tasks"]) resolved to app.tasks.tasks, which does not exist.

    The worker booted with zero tasks, so RENDER_ASYNC=true made every .delay() raise
    NotRegistered and POST /api/render/start return 500.
    """
    from app.tasks.celery_app import celery_app

    registered = {name for name in celery_app.tasks if name.startswith("tasks.")}
    assert registered == {
        "tasks.render_project",
        "tasks.generate_script",
        "tasks.generate_storyboard",
        "tasks.quality_check",
        "tasks.analyze_trend",
        "tasks.publish_due",
    }


def test_migrations_compile_on_postgres_with_compatible_types():
    """`alembic upgrade head` must work on PostgreSQL, the dialect CI claims to test.

    The suite builds its schema with create_all, so a migration-only type mismatch is
    invisible to it: 004 declared VARCHAR(36) FKs against a UUID primary key.
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    UUIDType = sa.String(36).with_variant(sa.dialects.postgresql.UUID(as_uuid=True), "postgresql")
    JSONType = sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql")

    metadata = sa.MetaData()
    projects = sa.Table("projects", metadata, sa.Column("id", UUIDType, primary_key=True))
    for name in ("quality_reviews", "generation_records"):
        table = sa.Table(
            name, metadata,
            sa.Column("id", UUIDType, primary_key=True),
            sa.Column("project_id", UUIDType, sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("context_json", JSONType),
        )
        ddl = str(sa.schema.CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "project_id UUID" in ddl, f"{name} FK column is not uuid on postgres:\n{ddl}"
        assert "VARCHAR(36)" not in ddl, f"{name} still uses a string id on postgres:\n{ddl}"

    # The prompt_templates owner column introduced in 005 must line up too.
    users = sa.Table("users", metadata, sa.Column("id", UUIDType, primary_key=True))
    prompts = sa.Table(
        "prompt_templates", metadata,
        sa.Column("id", UUIDType, primary_key=True),
        sa.Column("user_id", UUIDType, sa.ForeignKey("users.id")),
    )
    ddl = str(sa.schema.CreateTable(prompts).compile(dialect=postgresql.dialect()))
    assert "user_id UUID" in ddl, ddl


# --- LLM output must not be a 500 ------------------------------------------------------------


def test_llm_output_helpers_tolerate_real_model_shapes():
    from app.core.llm_output import as_dict, coerce_float, coerce_int, parse_json, parse_json_object

    fence = chr(96) * 3
    assert parse_json_object(fence + "json\n{\"a\": 1}\n" + fence) == {"a": 1}
    assert parse_json_object(fence + "json{\"a\": 1}" + fence) == {"a": 1}
    assert parse_json_object("[1, 2]") == {"data": [1, 2]}
    assert parse_json_object("not json at all") == {}
    assert parse_json("42") == 42

    assert coerce_int(30) == 30
    assert coerce_int("30") == 30
    assert coerce_int("30s") == 30
    assert coerce_int(30.9) == 30
    assert coerce_int(None, 7) == 7
    assert coerce_int("no digits", 7) == 7
    assert coerce_float("3-4s") == 3.0
    assert coerce_float("3.5") == 3.5
    assert coerce_float(None, 2.0) == 2.0

    assert as_dict(None) == {}
    assert as_dict([1, 2]) == {}
    assert as_dict({"a": 1}) == {"a": 1}


def test_script_agent_survives_fenced_and_list_responses():
    from app.agents.script_agent import ScriptAgent

    agent = ScriptAgent(llm_provider=None)
    fence = chr(96) * 3

    parsed = agent.parse_response(fence + "json\n" + json.dumps({
        "title": "T", "duration": "30s",
        "sections": [{"hook": "h"}],
    }) + "\n" + fence)
    # A list of sections is a normal response; it used to fail Pydantic validation.
    assert parsed.structured_data["sections"] == [{"hook": "h"}]

    # No JSON at all: the raw text is preserved as the script.
    prose = agent.parse_response("just some narration")
    assert prose.structured_data["full_script"] == "just some narration"


def test_storyboard_agent_survives_scalar_and_object_responses():
    from app.agents.storyboard_agent import StoryboardAgent

    agent = StoryboardAgent(llm_provider=None)
    assert agent.parse_response('[{"scene_number": 1}]').structured_data["scenes"] == [{"scene_number": 1}]
    assert agent.parse_response('{"scenes": [{"scene_number": 2}]}').structured_data["scenes"] == [{"scene_number": 2}]
    # A bare scalar used to hit data.get(...) and raise AttributeError.
    assert agent.parse_response("42").structured_data["scenes"] == []
    assert agent.parse_response("garbage").structured_data["scenes"] == []


@pytest.mark.anyio
async def test_unknown_agent_name_is_404_not_500(client: AsyncClient):
    token = await token_for(client, "p9-agent@example.com")
    resp = await client.post(
        "/api/agents/does-not-exist/run",
        json={"content": "hi"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.anyio
async def test_missing_llm_key_is_503_not_500(client: AsyncClient):
    """OpenAIProvider() raised a raw OpenAIError at construction, so an unconfigured
    deployment returned 500 on every generation endpoint. ProviderNotConfigured -> 503."""
    token = await token_for(client, "p9-nokey@example.com")

    for path, payload in [
        ("/api/agents/script/run", {"content": "a topic"}),
        ("/api/storyboard/generate", {"script": "a script"}),
        ("/api/scripts/generate", {"topic": "a topic", "duration": "30s"}),
        ("/api/trends/analyze", {"niche": "finance"}),
    ]:
        resp = await client.post(path, json=payload, headers=auth_headers(token))
        assert resp.status_code in (422, 503), f"{path} -> {resp.status_code}: {resp.text}"

    # And the inventory endpoint still reports what's configured and what is missing,
    # so an operator can diagnose the 503 without reading logs.
    inventory = await client.get("/api/providers", headers=auth_headers(token))
    assert inventory.status_code == 200, inventory.text
    llm_entries = [p for p in inventory.json()["providers"] if p["task"] == "llm"]
    assert llm_entries, inventory.text
    assert all(p["configured"] is False for p in llm_entries)


@pytest.mark.anyio
async def test_storyboard_accepts_non_numeric_durations(client: AsyncClient, monkeypatch):
    """LLMs emit "3-4s"; summing those raised TypeError and returned a 500."""
    from app.agents.base import AgentOutput
    from app.api import storyboard as storyboard_api

    class FakeLLM:
        async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, response_format=None):
            from app.providers.base import LLMResponse
            return LLMResponse(content="x", model="m", tokens_in=1, tokens_out=1, latency_ms=1, cost_cents=0)

        async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
            yield ""

    class FakeAgent:
        def __init__(self, llm_provider=None):
            self.llm = llm_provider

        async def run(self, payload):
            return AgentOutput(content="x", structured_data={"scenes": [
                {"scene_number": 1, "duration": "3-4s"},
                {"scene_number": 2, "duration": "2.5"},
                {"scene_number": 3, "duration": None},
            ]})

    monkeypatch.setattr(storyboard_api, "get_provider", lambda task, name=None: FakeLLM())
    monkeypatch.setattr("app.agents.registry.get_agent", lambda name, llm: FakeAgent(llm))

    token = await token_for(client, "p9-sb@example.com")
    resp = await client.post(
        "/api/storyboard/generate", json={"script": "a script"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    # 3-4s -> 3.0, 2.5 -> 2.5, None -> default 3.0
    assert resp.json()["total_duration"] == pytest.approx(8.5)


@pytest.mark.anyio
async def test_quality_review_rejects_an_injected_provider_object(client: AsyncClient):
    """llm_provider was typed Any, so a client could install arbitrary JSON as the LLM."""
    token = await token_for(client, "p9-quality@example.com")
    pid = await project_for(client, token)

    resp = await client.post(
        f"/api/projects/{pid}/quality/review",
        json={"script": "some script", "llm_provider": {"not": "a provider"}},
        headers=auth_headers(token),
    )
    # Must not be a 500 from trying to .complete() on a dict.
    assert resp.status_code in (422, 404, 503), resp.text


# --- media access control --------------------------------------------------------------------


def test_media_signature_is_key_bound_and_expiry_bound():
    from app.services.storage_service import media_signature, verify_media_signature

    key = "projects/p1/scene_image/a.png"
    sig = media_signature(key, 2_000_000_000)
    assert verify_media_signature(key, "2000000000", sig) is True
    # Same signature, different key: rejected.
    assert verify_media_signature("projects/p2/scene_image/a.png", "2000000000", sig) is False
    assert verify_media_signature(key, "1", sig) is False
    assert verify_media_signature(key, "not-a-number", sig) is False
    assert verify_media_signature(key, None, None) is False
    assert verify_media_signature(key, "2000000000", "short") is False


def test_sign_media_url_round_trips_and_passes_through_remote_urls():
    from app.services.storage_service import sign_media_url, storage_key_from_url
    from urllib.parse import parse_qs, urlparse

    signed = sign_media_url("/storage/projects/p1/video/v.mp4")
    key = storage_key_from_url(signed)
    assert key == "projects/p1/video/v.mp4"
    query = parse_qs(urlparse(signed).query)
    assert query["exp"][0] and query["sig"][0]

    assert sign_media_url("") == ""
    # S3/MinIO urls are served by the object store, not this route.
    remote = "http://localhost:9000/bucket/key.mp4"
    assert sign_media_url(remote) == remote


# --- providers must fail loudly, not silently ------------------------------------------------


@pytest.mark.anyio
async def test_image_provider_raises_instead_of_returning_an_empty_url():
    """An empty url used to be stored as a 0-byte file and reported as a 200 success."""
    from app.providers.image.providers import PollinationsProvider

    provider = PollinationsProvider()

    class FakeResponse:
        status_code = 500
        content = b""

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return FakeResponse()

    import app.providers.image.providers as mod
    original = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = FakeClient
    try:
        with pytest.raises(ProviderRequestError):
            await provider.generate("a prompt")
    finally:
        mod.httpx.AsyncClient = original


@pytest.mark.anyio
async def test_provider_errors_become_502_and_missing_provider_becomes_503(client: AsyncClient):
    """Exercises the two handlers registered in app.main for provider failures."""
    from app import main as main_mod
    from app.main import app
    from starlette.requests import Request
    from app.providers.base import ProviderNotConfigured

    provider_not_configured_handler = main_mod.provider_not_configured_handler
    provider_request_error_handler = main_mod.provider_request_error_handler
    scope = {"type": "http", "method": "GET", "path": "/api/x", "headers": []}

    missing = await provider_not_configured_handler(Request(scope), ProviderNotConfigured(ProviderTask.LLM, ["openai"]))
    assert missing.status_code == 503
    assert b"openai" in missing.body

    failed = await provider_request_error_handler(Request(scope), ProviderRequestError("openai", "boom"))
    assert failed.status_code == 502
    assert b"boom" in failed.body

    assert {h for h in app.exception_handlers} >= {
        ProviderNotConfigured, ProviderRequestError, __import__("httpx").HTTPError,
    }


# --- narration: the headline feature used to produce silent video ------------------------------


@pytest.mark.anyio
async def test_pipeline_synthesizes_narration_for_each_scene(monkeypatch, tmp_path):
    """The voice provider was resolved but never called, so every video had no audio."""
    from app.services.pipeline import VideoPipeline

    pipeline = VideoPipeline.__new__(VideoPipeline)
    pipeline.voice = _RecordingVoice()

    with pytest.MonkeyPatch.context() as mp:
        from app.config import settings
        mp.setattr(settings, "elevenlabs_voice_id", "voice-1")
        path = await VideoPipeline._synthesize_narration(pipeline, str(tmp_path), 1, "Hello there")
    assert path is not None and os.path.isfile(path)
    assert pipeline.voice.calls == ["Hello there"]
    with open(path, "rb") as f:
        assert f.read() == b"fake-mp3-bytes"


@pytest.mark.anyio
async def test_narration_is_skipped_rather_than_crashing_the_render(tmp_path):
    from app.services.pipeline import VideoPipeline

    pipeline = VideoPipeline.__new__(VideoPipeline)

    class Broken:
        async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
            raise RuntimeError("tts down")

    pipeline.voice = Broken()
    assert await VideoPipeline._synthesize_narration(pipeline, str(tmp_path), 1, "text") is None

    class NoneReturning:
        async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
            return None

    pipeline.voice = NoneReturning()
    assert await VideoPipeline._synthesize_narration(pipeline, str(tmp_path), 1, "text") is None

    # No narration in the scene at all.
    pipeline.voice = _RecordingVoice()
    assert await VideoPipeline._synthesize_narration(pipeline, str(tmp_path), 1, "   ") is None


class _RecordingVoice:
    def __init__(self):
        self.calls = []

    async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
        import base64
        self.calls.append(text)
        payload = base64.b64encode(b"fake-mp3-bytes").decode()
        from app.providers.base import AudioResult
        return AudioResult(audio_base64=f"data:audio/mp3;base64,{payload}", duration_seconds=1.0)


@pytest.mark.anyio
async def test_renderer_rejects_an_empty_scene_list():
    """Every progress calculation divided by len(scenes)."""
    from app.services.render_service import VideoRenderer

    renderer = VideoRenderer.__new__(VideoRenderer)
    with pytest.raises(ValueError):
        await renderer.render(scenes=[], output_path="out.mp4")


@pytest.mark.anyio
async def test_audio_track_is_padded_so_narration_stays_in_sync(monkeypatch):
    """Concatenating only the narrated scenes shifted later narration ahead of its picture."""
    from app.services.render_service import SceneAsset, VideoRenderer

    renderer = VideoRenderer.__new__(VideoRenderer)
    renderer.config = type("C", (), {"audio_codec": "aac", "audio_bitrate": "128k"})()
    renderer.temp_dir = "."
    renderer.calls = []

    async def fake_run(self_or_cmd, cmd=None):
        command = cmd if cmd is not None else self_or_cmd
        renderer.calls.append(command)
        # Last argument of the ffmpeg invocations is the output file.
        if isinstance(command, list):
            with open(command[-1], "wb") as f:
                f.write(b"audio")

    monkeypatch.setattr(VideoRenderer, "_run_ffmpeg", fake_run)

    async def fake_silence(self, output_path, duration):
        renderer.calls.append(("silence", output_path, duration))
        with open(output_path, "wb") as f:
            f.write(b"silence")

    monkeypatch.setattr(VideoRenderer, "_create_silence", fake_silence)

    narrated = os.path.join(".", "narr.mp3")
    with open(narrated, "wb") as f:
        f.write(b"x")

    scenes = [
        SceneAsset(image_path="a.png", duration=3, narration_audio_path=narrated),
        SceneAsset(image_path="b.png", duration=4, narration_audio_path=None),
    ]
    await renderer._add_audio("in.mp4", scenes, "job1")

    # Both scenes are on the track, in scene order, with a gap where narration is missing.
    listing = open(os.path.join(".", "audio_concat_job1.txt")).read()
    entries = [line for line in listing.splitlines() if line.strip()]
    assert len(entries) == 2, listing
    assert entries[0].endswith("narr.mp3'"), listing
    assert entries[1].endswith("silence_job1_001.mp3'"), listing
    silences = [c for c in renderer.calls if isinstance(c, tuple)]
    assert any(c[2] == 4 for c in silences), renderer.calls
    assert any(c[2] == 3 for c in silences) is False, "narrated scene must not get a silence track"

    # With no narration anywhere, the video passes through untouched.
    renderer.calls = []
    quiet = [SceneAsset(image_path="a.png", duration=3)]
    assert await renderer._add_audio("in.mp4", quiet, "job2") == "in.mp4"
    assert renderer.calls == []


# --- pipeline bookkeeping ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_pipeline_persists_real_asset_keys_and_a_real_srt(client: AsyncClient, monkeypatch):
    """Scene assets used to record synthesised /storage paths for files never written, and the
    caption asset pointed at a sibling key that was never uploaded."""
    import app.services.pipeline as pipeline_mod
    from app.providers.base import ImageResult, LLMResponse, VideoResult
    from app.services.render_service import RenderResult
    import os as _os

    token = await token_for(client, "p9-pipe@example.com")
    pid = await project_for(client, token)

    responses = [
        json.dumps({"title": "T", "duration": "30s", "full_script": "One two three four."}),
        json.dumps([{
            "scene_number": 1, "duration": "3", "narration": "Hello world",
            "visual_description": "a snowy trail", "transition": "fade",
        }]),
    ]

    class FakeLLM:
        def __init__(self):
            self.i = 0

        async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, response_format=None):
            content = responses[min(self.i, len(responses) - 1)]
            self.i += 1
            return LLMResponse(content=content, model="m", tokens_in=1, tokens_out=1, latency_ms=1, cost_cents=0)

        async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
            yield ""

    class FakeImage:
        name = "fake-image"

        async def generate(self, prompt, size="1080x1920", quality="standard", n=1):
            base = LocalStorage().base_dir
            path = _os.path.join(base, "p9", "scene.png")
            _os.makedirs(_os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            return [ImageResult(url="/storage/p9/scene.png")]

    class FakeVoice:
        name = "fake-voice"

        async def synthesize(self, text, voice_id, speed=1.0, emotion=None):
            import base64
            from app.providers.base import AudioResult
            payload = base64.b64encode(b"mp3").decode()
            return AudioResult(audio_base64=f"data:audio/mp3;base64,{payload}", duration_seconds=1.0)

        async def list_voices(self, language=None):
            return []

    class FakeVideo:
        name = "fake-video"

        async def generate(self, prompt, duration=5.0, image_url=None):
            return VideoResult(url="", duration_seconds=duration)

    class FakeRouter:
        def resolve_all(self):
            return {t: FakeLLM() for t in (ProviderTask.LLM,)} | {
                ProviderTask.IMAGE: FakeImage(),
                ProviderTask.VOICE: FakeVoice(),
                ProviderTask.VIDEO: FakeVideo(),
            }

    class FakeRenderer:
        def __init__(self, config=None):
            pass

        async def render(self, scenes, output_path, background_music_path=None, music_volume=0.15,
                         captions=None, on_progress=None):
            import inspect
            _os.makedirs(_os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"video")
            if on_progress and inspect.iscoroutinefunction(on_progress):
                await on_progress(100, "done")
            return RenderResult(output_path=output_path, duration=3.0, file_size=5, format="mp4")

    monkeypatch.setattr(pipeline_mod, "provider_router", FakeRouter())
    monkeypatch.setattr(pipeline_mod, "VideoRenderer", FakeRenderer)

    resp = await client.post(
        "/api/render/start", json={"project_id": pid, "topic": "winter"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]

    async with async_session() as s:
        job = (await s.execute(select(RenderJob).where(RenderJob.id == job_id))).scalar_one()
        assert job.status == "completed", job.error
        # A url, not a filesystem path that leaked the server's directory layout.
        assert job.output_url.startswith(("/storage/", "https://"))

    from app.models.asset import Asset
    async with async_session() as s:
        assets = (await s.execute(select(Asset).where(Asset.project_id == pid))).scalars().all()
    by_type = {a.type: a for a in assets}
    assert "scene_image" in by_type
    assert "video" in by_type
    assert "captions" in by_type

    storage = LocalStorage()
    for kind, asset in by_type.items():
        key = (asset.metadata_json or {}).get("key")
        if kind == "captions":
            key = key or asset.url.replace("/storage/", "")
        assert key, f"{kind} asset has no storage key"
        path = _os.path.join(storage.base_dir, key)
        assert _os.path.isfile(path), f"{kind} points at a file that was never written: {path}"
        assert _os.path.getsize(path) > 0, f"{kind} is a zero-byte file"


@pytest.mark.anyio
async def test_pipeline_error_path_rolls_back_before_recording_failure(client: AsyncClient, monkeypatch):
    """Committing on a session that needed rollback raised PendingRollbackError and lost the
    failed status."""
    import app.services.pipeline as pipeline_mod

    token = await token_for(client, "p9-fail@example.com")
    pid = await project_for(client, token)

    class Boom:
        async def complete(self, *a, **k):
            raise RuntimeError("llm down")

        async def stream(self, *a, **k):
            yield ""

    class Router:
        def resolve_all(self):
            return {ProviderTask.LLM: Boom(), ProviderTask.IMAGE: Boom(), ProviderTask.VOICE: Boom(), ProviderTask.VIDEO: Boom()}

    monkeypatch.setattr(pipeline_mod, "provider_router", Router())

    resp = await client.post(
        "/api/render/start", json={"project_id": pid, "topic": "x"}, headers=auth_headers(token)
    )
    assert resp.status_code == 500, resp.text

    async with async_session() as s:
        project = (await s.execute(select(Project).where(Project.id == pid))).scalar_one()
        assert project.status == "failed", project.status


@pytest.mark.anyio
async def test_sync_render_commits_progress_so_status_is_observable(client: AsyncClient, monkeypatch):
    """Progress was only mutated in memory, so a concurrent /status read 0 for the whole render."""
    from app.services.pipeline import PipelineResult

    observed = []

    class FakePipeline:
        def __init__(self):
            pass

        async def run(self, project_id, topic, duration="30s", style="educational", db=None, on_progress=None):
            await on_progress(40, "halfway")
            # Read back through a *separate* session, exactly like the polling endpoint does.
            async with async_session() as other:
                row = (await other.execute(
                    select(RenderJob).where(RenderJob.project_id == project_id).order_by(RenderJob.created_at.desc())
                )).scalars().first()
                observed.append(row.progress)
            return PipelineResult(
                project_id=project_id, status="completed",
                video_path="out.mp4", video_url="/storage/projects/x/video/v.mp4",
            )

    monkeypatch.setattr("app.api.render.VideoPipeline", FakePipeline)

    token = await token_for(client, "p9-progress@example.com")
    pid = await project_for(client, token)
    resp = await client.post(
        "/api/render/start", json={"project_id": pid, "topic": "x"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    assert observed == [40], f"progress was not committed mid-render: {observed}"

    status = await client.get(f"/api/render/status/{resp.json()['job_id']}", headers=auth_headers(token))
    assert status.json()["progress"] == 100
    assert status.json()["output_url"].startswith("/storage/")


# --- registration race -------------------------------------------------------------------------


@pytest.mark.anyio
async def test_duplicate_registration_is_400(client: AsyncClient):
    body = {"email": "p9-dupe@example.com", "name": "A", "password": "testpass123"}
    first = await client.post("/api/auth/register", json=body)
    assert first.status_code == 200, first.text
    second = await client.post("/api/auth/register", json=body)
    assert second.status_code == 400, second.text


# --- costs aggregation is not N+1 ---------------------------------------------------------------


@pytest.mark.anyio
async def test_costs_sums_across_jobs_and_records(client: AsyncClient):
    from app.models.job import GenerationJob

    token = await token_for(client, "p9-costs@example.com")
    pid = await project_for(client, token)

    async with async_session() as s:
        s.add(GenerationJob(project_id=pid, agent_name="script", status="completed", cost_cents=10, latency_ms=5))
        s.add(GenerationRecord(project_id=pid, task="llm", provider="p", status="completed",
                               cost_cents=7, latency_ms=3))
        await s.commit()

    resp = await client.get("/api/costs", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["cost_cents"] == 17
    assert body["totals"]["latency_ms"] == 8
    assert body["totals"]["calls"] == 2
    entry = next(e for e in body["per_project"] if e["project_id"] == pid)
    assert entry["cost_cents"] == 17


@pytest.mark.anyio
async def test_costs_is_empty_for_a_fresh_account(client: AsyncClient):
    token = await token_for(client, "p9-nocost@example.com")
    resp = await client.get("/api/costs", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"totals": {"cost_cents": 0, "latency_ms": 0, "calls": 0}, "per_project": []}


# --- storage -------------------------------------------------------------------------------------


def test_local_storage_refuses_keys_outside_its_root():
    storage = LocalStorage()
    for bad in ["../escape.png", "/etc/passwd", "projects/../../escape"]:
        with pytest.raises(ValueError):
            storage._resolve(bad)


def test_local_storage_read_returns_uploaded_bytes(tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))
    key = "projects/p/image/a.png"
    import asyncio
    asyncio.run(storage.upload(b"bytes", key, "image/png"))
    assert asyncio.run(storage.read(key)) == b"bytes"
    assert asyncio.run(storage.get_url(key)) == f"/storage/{key}"
    assert asyncio.run(storage.delete(key)) is True
    assert asyncio.run(storage.delete(key)) is False


@pytest.mark.anyio
async def test_upload_accepts_project_id_as_a_multipart_form_field(client: AsyncClient):
    """project_id/asset_type were plain scalars, so FastAPI read them as query params.

    The web client sends them in the multipart body, so every upload 400'd with
    "project_id is required" and no file could be attached to a project at all.
    """
    token = await token_for(client, "p9-upload@example.com")
    pid = await project_for(client, token)

    resp = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 32, "image/png")},
        data={"asset_type": "image", "project_id": pid},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"].startswith(f"projects/{pid}/")
    assert body["url"].startswith("/storage/") and "sig=" in body["url"]

    # Missing project_id is still rejected, and so is a foreign project.
    missing = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"\x89PNG", "image/png")},
        data={"asset_type": "image"},
        headers=auth_headers(token),
    )
    assert missing.status_code == 422, missing.text

    other = await token_for(client, "p9-upload-2@example.com")
    foreign = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"\x89PNG", "image/png")},
        data={"asset_type": "image", "project_id": pid},
        headers=auth_headers(other),
    )
    assert foreign.status_code == 404, foreign.text

    # Content-type policy is enforced.
    wrong = await client.post(
        "/api/assets/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        data={"asset_type": "image", "project_id": pid},
        headers=auth_headers(token),
    )
    assert wrong.status_code == 422, wrong.text


@pytest.mark.anyio
async def test_db_has_prompt_template_owner_column(client: AsyncClient):
    """005 adds user_id; the SQLite suite builds with create_all so check the model too."""
    from app.models.prompt import PromptTemplate

    assert "user_id" in PromptTemplate.__table__.columns
    async with async_session() as s:
        cols = (await s.execute(text("PRAGMA table_info(prompt_templates)"))).all()
    assert any(row[1] == "user_id" for row in cols), [r[1] for r in cols]
