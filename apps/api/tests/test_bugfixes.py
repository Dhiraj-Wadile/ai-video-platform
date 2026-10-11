"""Regression tests for the bug sweep: response-model 500s, asset hardening, aggregation, validation."""
import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.asset import Asset
from app.models.character import Character
from app.models.job import GenerationJob
from app.models.prompt import PromptTemplate
from app.models.script import Scene
from app.models.trend import Trend, VideoAnalytics
from app.models.user import User
from app.services.storage_service import ALLOWED_ASSET_TYPES, LocalStorage, generate_asset_key


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def token_for(client: AsyncClient, email: str) -> str:
    await client.post("/api/auth/register", json={
        "email": email, "name": "Bug User", "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def project_for(client: AsyncClient, token: str, name: str = "P") -> str:
    resp = await client.post(
        "/api/projects", json={"name": name, "project_type": "short_form"}, headers=auth(token)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def first_user_id() -> str:
    async with async_session() as s:
        return (await s.execute(select(User.id))).scalar_one()


async def user_id_for(client: AsyncClient, token: str) -> str:
    """Resolve the caller's id from their token (the `sub` claim)."""
    from app.core.security import verify_token
    user_id = verify_token(token)
    assert user_id, "token should carry a subject"
    return user_id


# --- response models: datetime columns must serialize, not 500 ---------------------------


@pytest.mark.anyio
async def test_list_characters_returns_rows(client: AsyncClient):
    token = await token_for(client, "fix-chars@example.com")
    async with async_session() as s:
        s.add(Character(user_id=await first_user_id(), name="Ada", appearance="tall"))
        await s.commit()

    resp = await client.get("/api/characters", headers=auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert isinstance(body[0]["created_at"], str)
    assert body[0]["name"] == "Ada"


@pytest.mark.anyio
async def test_character_patch_persists_voice_config(client: AsyncClient):
    token = await token_for(client, "fix-voice@example.com")
    async with async_session() as s:
        character = Character(user_id=await first_user_id(), name="Grace")
        s.add(character)
        await s.commit()
        character_id = str(character.id)

    resp = await client.patch(
        f"/api/characters/{character_id}",
        json={"voice_config": {"pitch": "low"}, "speaking_style": "calm"},
        headers=auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["voice_config"] == {"pitch": "low"}

    async with async_session() as s:
        stored = (await s.execute(
            select(Character).where(Character.id == character_id)
        )).scalar_one()
        assert stored.voice_config_json == {"pitch": "low"}


@pytest.mark.anyio
async def test_character_patch_rejects_unknown_field(client: AsyncClient):
    token = await token_for(client, "fix-unknown@example.com")
    async with async_session() as s:
        character = Character(user_id=await first_user_id(), name="Nope")
        s.add(character)
        await s.commit()
        character_id = str(character.id)

    resp = await client.patch(
        f"/api/characters/{character_id}",
        json={"name": None},
        headers=auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_trends_serializes(client: AsyncClient):
    token = await token_for(client, "fix-trends@example.com")
    async with async_session() as s:
        s.add(Trend(topic="AI video", source="test", score=91.5, metadata_json={"format": "short"}))
        await s.commit()

    resp = await client.get("/api/trends", headers=auth(token))
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()[0]["discovered_at"], str)


@pytest.mark.anyio
async def test_list_prompts_serializes_and_patches(client: AsyncClient):
    from sqlalchemy import insert
    import uuid as _uuid

    token = await token_for(client, "fix-prompts@example.com")
    user_id = await user_id_for(client, token)
    async with async_session() as s:
        # Core insert so the column default is bypassed: this is the NULL-version row that used to
        # make `prompt.version += 1` raise.
        await s.execute(insert(PromptTemplate.__table__).values(
            id=str(_uuid.uuid4()), name="Base", category="script", content="v1", version=None,
            user_id=user_id,
        ))
        await s.commit()

    resp = await client.get("/api/prompts", headers=auth(token))
    assert resp.status_code == 200, resp.text
    prompt_id = resp.json()[0]["id"]

    patched = await client.patch(
        f"/api/prompts/{prompt_id}", json={"content": "v2"}, headers=auth(token)
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["version"] == 1


@pytest.mark.anyio
async def test_prompt_templates_are_not_cross_tenant_writable(client: AsyncClient):
    """A template owned by one user must not be editable by another (Phase 9 hardening)."""
    token_a = await token_for(client, "prompt-owner@example.com")
    token_b = await token_for(client, "prompt-other@example.com")

    created = await client.post(
        "/api/prompts",
        json={"name": "Mine", "category": "script", "content": "v1"},
        headers=auth(token_a),
    )
    assert created.status_code == 201, created.text
    prompt_id = created.json()["id"]

    cross = await client.patch(
        f"/api/prompts/{prompt_id}", json={"content": "hijacked"}, headers=auth(token_b)
    )
    assert cross.status_code == 404, cross.text

    own = await client.patch(
        f"/api/prompts/{prompt_id}", json={"content": "v2"}, headers=auth(token_a)
    )
    assert own.status_code == 200, own.text

    deleted = await client.delete(f"/api/prompts/{prompt_id}", headers=auth(token_b))
    assert deleted.status_code == 404, deleted.text


@pytest.mark.anyio
async def test_global_prompt_template_is_read_only(client: AsyncClient):
    token = await token_for(client, "prompt-global@example.com")
    from sqlalchemy import insert
    import uuid as _uuid

    async with async_session() as s:
        await s.execute(insert(PromptTemplate.__table__).values(
            id=str(_uuid.uuid4()), name="Shipped", category="script", content="v1",
            user_id=None,
        ))
        await s.commit()

    resp = await client.get("/api/prompts", headers=auth(token))
    global_id = next(p["id"] for p in resp.json() if p["name"] == "Shipped")

    patched = await client.patch(
        f"/api/prompts/{global_id}", json={"content": "v2"}, headers=auth(token)
    )
    assert patched.status_code == 403, patched.text


# --- storage: no path traversal, no wrong-type or oversized uploads -----------------------


def test_generate_asset_key_rejects_traversal():
    for bad in ["../../../evil", "..", "a/b", "a\\b", "", "UPPER!", "x" * 40]:
        with pytest.raises(ValueError):
            generate_asset_key("proj", bad, "png")


def test_generate_asset_key_allows_internal_kinds():
    assert generate_asset_key("proj-1", "scene_image", "png").startswith("projects/proj-1/scene_image/")
    assert generate_asset_key("proj-1", "video", "mp4").endswith(".mp4")


def test_local_storage_refuses_escape(tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path / "storage"))
    with pytest.raises(ValueError):
        asyncio.run(storage.upload(b"x", "../escaped.png"))
    with pytest.raises(ValueError):
        asyncio.run(storage.upload(b"x", "/etc/passwd"))
    with pytest.raises(ValueError):
        asyncio.run(storage.delete("../../outside"))


@pytest.mark.anyio
async def test_upload_rejects_bad_type_and_creates_asset_row(client: AsyncClient):
    token = await token_for(client, "fix-upload@example.com")
    pid = await project_for(client, token)

    traversal = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"x", "image/png")},
        params={"asset_type": "../../../evil", "project_id": pid},
        headers=auth(token),
    )
    assert traversal.status_code == 422

    wrong_media = await client.post(
        "/api/assets/upload",
        files={"file": ("a.exe", b"x", "application/x-msdownload")},
        params={"asset_type": "image", "project_id": pid},
        headers=auth(token),
    )
    assert wrong_media.status_code == 422

    ok = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"x", "image/png")},
        params={"asset_type": "image", "project_id": pid},
        headers=auth(token),
    )
    assert ok.status_code == 200, ok.text

    async with async_session() as s:
        rows = (await s.execute(
            select(Asset).where(Asset.project_id == pid)
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].metadata_json["key"] == ok.json()["key"]


# --- analytics: snapshots must not be double counted --------------------------------------


@pytest.mark.anyio
async def test_analytics_counts_latest_snapshot_only(client: AsyncClient):
    token = await token_for(client, "fix-analytics@example.com")
    pid = await project_for(client, token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with async_session() as s:
        s.add(VideoAnalytics(
            project_id=pid, platform="tiktok", views=100, likes=10, comments=1, shares=1,
            fetched_at=now.replace(hour=0, minute=0, second=0),
        ))
        s.add(VideoAnalytics(
            project_id=pid, platform="tiktok", views=250, likes=25, comments=2, shares=3,
            fetched_at=now,
        ))
        await s.commit()

    body = (await client.get("/api/analytics", headers=auth(token))).json()
    assert body["total_views"] == 250
    assert body["video_count"] == 1
    assert len(body["videos"]) == 1


# --- agent runs: rows without a timestamp must not crash ------------------------------------


@pytest.mark.anyio
async def test_agent_runs_tolerates_missing_created_at(client: AsyncClient):
    token = await token_for(client, "fix-runs@example.com")
    pid = await project_for(client, token)

    async with async_session() as s:
        s.add(GenerationJob(project_id=pid, agent_name="script", status="completed", created_at=None))
        s.add(GenerationJob(
            project_id=pid, agent_name="storyboard", status="completed",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        await s.commit()

    resp = await client.get("/api/agents/runs", headers=auth(token))
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["runs"]) == 2


# --- input validation ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_project_update_rejects_null_and_unknown_status(client: AsyncClient):
    token = await token_for(client, "fix-validate@example.com")
    pid = await project_for(client, token)

    nulled = await client.patch(f"/api/projects/{pid}", json={"name": None}, headers=auth(token))
    assert nulled.status_code == 422

    bad_status = await client.patch(f"/api/projects/{pid}", json={"status": "banana"}, headers=auth(token))
    assert bad_status.status_code == 422

    ok = await client.patch(
        f"/api/projects/{pid}", json={"status": "ready", "name": "Renamed"}, headers=auth(token)
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ready"


@pytest.mark.anyio
async def test_scene_update_validates_duration(client: AsyncClient):
    token = await token_for(client, "fix-scene@example.com")
    pid = await project_for(client, token)

    async with async_session() as s:
        scene = Scene(project_id=pid, scene_number=1, duration=3, narration="n")
        s.add(scene)
        await s.commit()
        scene_id = str(scene.id)

    for bad in [0, -5, 10_000]:
        resp = await client.patch(
            f"/api/projects/{pid}/scenes/{scene_id}", json={"duration": bad}, headers=auth(token)
        )
        assert resp.status_code == 422, bad

    good = await client.patch(
        f"/api/projects/{pid}/scenes/{scene_id}", json={"duration": 5}, headers=auth(token)
    )
    assert good.status_code == 200
    assert good.json()["duration"] == 5


@pytest.mark.anyio
async def test_trend_analyze_requires_topic(client: AsyncClient):
    token = await token_for(client, "fix-analyze@example.com")
    resp = await client.post("/api/trends/analyze", json={}, headers=auth(token))
    assert resp.status_code == 422


# --- media is actually served ---------------------------------------------------------------


@pytest.mark.anyio
async def test_media_is_served_only_with_a_valid_signature(client: AsyncClient):
    """Media bytes must not be world-readable.

    This used to be a bare StaticFiles mount, so any URL a user could see - including a
    deleted project's renders - was fetchable by anyone.
    """
    from app.services.storage_service import get_storage, sign_media_url

    token = await token_for(client, "fix-static@example.com")
    pid = await project_for(client, token)
    storage = get_storage()
    key = generate_asset_key(pid, "image", ALLOWED_ASSET_TYPES["image"])
    await storage.upload(b"image-bytes", key, "image/png")

    unsigned = await client.get(f"/storage/{key}")
    assert unsigned.status_code == 403, unsigned.text

    tampered = await client.get(f"/storage/{key}?exp=99999999999&sig=deadbeef")
    assert tampered.status_code == 403, tampered.text

    expired = await client.get(sign_media_url(f"/storage/{key}", ttl_seconds=-10))
    assert expired.status_code == 403, expired.text

    signed = await client.get(sign_media_url(f"/storage/{key}"))
    assert signed.status_code == 200, signed.text
    assert signed.content == b"image-bytes"


@pytest.mark.anyio
async def test_asset_api_returns_a_usable_signed_url(client: AsyncClient):
    """The ownership-checked endpoint is what mints signed URLs, so <img src> still works."""
    token = await token_for(client, "fix-signed@example.com")
    pid = await project_for(client, token)

    uploaded = await client.post(
        "/api/assets/upload",
        params={"project_id": pid, "asset_type": "image"},
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=auth(token),
    )
    assert uploaded.status_code == 200, uploaded.text
    url = uploaded.json()["url"]
    assert "sig=" in url, url

    fetched = await client.get(url)
    assert fetched.status_code == 200, fetched.text

    # The database stores a stable key, never the expiring signed URL.
    async with async_session() as s:
        row = (await s.execute(select(Asset).where(Asset.project_id == pid))).scalars().first()
        assert "sig=" not in (row.url or "")
