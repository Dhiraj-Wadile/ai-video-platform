import pytest
from httpx import AsyncClient

from app.database import async_session
from app.models.job import RenderJob
from app.models.script import Script
from app.models.trend import VideoAnalytics


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def token_for(client: AsyncClient, email: str) -> str:
    await client.post("/api/auth/register", json={
        "email": email, "name": "Sec User", "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def project_for(client: AsyncClient, token: str, name: str) -> str:
    resp = await client.post(
        "/api/projects", json={"name": name, "project_type": "short_form"}, headers=auth(token)
    )
    return resp.json()["id"]


@pytest.mark.anyio
async def test_render_status_is_scoped_to_owner(client: AsyncClient):
    token_a = await token_for(client, "sec-render-a@example.com")
    token_b = await token_for(client, "sec-render-b@example.com")
    pid_a = await project_for(client, token_a, "A project")

    async with async_session() as s:
        job = RenderJob(project_id=pid_a, status="completed", progress=100, output_url="/storage/a.mp4")
        s.add(job)
        await s.commit()
        job_id = str(job.id)

    assert (await client.get(f"/api/render/status/{job_id}", headers=auth(token_a))).status_code == 200
    assert (await client.get(f"/api/render/status/{job_id}", headers=auth(token_b))).status_code == 404
    assert (await client.get(f"/api/render/status/{job_id}")).status_code == 401


@pytest.mark.anyio
async def test_script_read_is_scoped_to_owner(client: AsyncClient):
    token_a = await token_for(client, "sec-script-a@example.com")
    token_b = await token_for(client, "sec-script-b@example.com")
    pid_a = await project_for(client, token_a, "Script project")

    async with async_session() as s:
        script = Script(project_id=pid_a, title="Secret", content="private words")
        s.add(script)
        await s.commit()
        script_id = str(script.id)

    own = await client.get(f"/api/scripts/{script_id}", headers=auth(token_a))
    assert own.status_code == 200
    assert own.json()["content"] == "private words"

    assert (await client.get(f"/api/scripts/{script_id}", headers=auth(token_b))).status_code == 404
    assert (await client.get(f"/api/scripts/{script_id}")).status_code == 401


@pytest.mark.anyio
async def test_analytics_scoped_to_owner(client: AsyncClient):
    token_a = await token_for(client, "sec-analytics-a@example.com")
    token_b = await token_for(client, "sec-analytics-b@example.com")
    pid_a = await project_for(client, token_a, "Analytics A")
    pid_b = await project_for(client, token_b, "Analytics B")

    async with async_session() as s:
        s.add(VideoAnalytics(project_id=pid_a, views=1000, likes=100, comments=10, shares=5))
        s.add(VideoAnalytics(project_id=pid_b, views=50, likes=1))
        await s.commit()

    data_a = (await client.get("/api/analytics", headers=auth(token_a))).json()
    data_b = (await client.get("/api/analytics", headers=auth(token_b))).json()

    assert data_a["total_views"] == 1000
    assert data_a["video_count"] == 1
    assert [v["project_id"] for v in data_a["videos"]] == [pid_a]
    assert data_a["videos"][0]["title"] == "Analytics A"

    assert data_b["total_views"] == 50
    assert [v["project_id"] for v in data_b["videos"]] == [pid_b]

    assert (await client.get(f"/api/analytics/{pid_a}", headers=auth(token_b))).status_code == 404
    assert (await client.get(f"/api/analytics/{pid_a}", headers=auth(token_a))).status_code == 200


@pytest.mark.anyio
async def test_assets_are_scoped_to_owner(client: AsyncClient):
    token_a = await token_for(client, "sec-assets-a@example.com")
    token_b = await token_for(client, "sec-assets-b@example.com")
    pid_a = await project_for(client, token_a, "Assets A")
    pid_b = await project_for(client, token_b, "Assets B")

    uploaded = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"fake-bytes", "image/png")},
        params={"asset_type": "image", "project_id": pid_a},
        headers=auth(token_a),
    )
    assert uploaded.status_code == 200
    key = uploaded.json()["key"]
    assert key.startswith(f"projects/{pid_a}/")

    assert (await client.get(f"/api/assets/{key}", headers=auth(token_a))).status_code == 200
    assert (await client.get(f"/api/assets/{key}", headers=auth(token_b))).status_code == 404
    assert (await client.get(f"/api/assets/{key}")).status_code == 401

    foreign_upload = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"fake-bytes", "image/png")},
        params={"asset_type": "image", "project_id": pid_b},
        headers=auth(token_a),
    )
    assert foreign_upload.status_code == 404

    no_project = await client.post(
        "/api/assets/upload",
        files={"file": ("a.png", b"fake-bytes", "image/png")},
        params={"asset_type": "image"},
        headers=auth(token_a),
    )
    assert no_project.status_code == 422


@pytest.mark.anyio
async def test_unscoped_asset_key_is_rejected(client: AsyncClient):
    token = await token_for(client, "sec-assets-c@example.com")
    resp = await client.get("/api/assets/some-loose-file.png", headers=auth(token))
    assert resp.status_code == 404
