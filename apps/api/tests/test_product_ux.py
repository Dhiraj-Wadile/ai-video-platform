import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.job import GenerationJob
from app.models.script import Scene


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_token(client: AsyncClient, email: str = "ux@example.com") -> str:
    await client.post("/api/auth/register", json={
        "email": email,
        "name": "UX User",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def create_project(client: AsyncClient, token: str, name: str = "P") -> str:
    proj = await client.post("/api/projects", json={"name": name, "project_type": "short_form"},
                             headers=auth_headers(token))
    return proj.json()["id"]


@pytest.mark.anyio
async def test_scene_patch_updates_fields(client: AsyncClient):
    token = await get_token(client)
    pid = await create_project(client, token)

    async with async_session() as s:
        scene = Scene(project_id=pid, scene_number=1, duration=3,
                      visual_description="Old", narration="n")
        s.add(scene)
        await s.commit()
        scene_id = str(scene.id)

    resp = await client.patch(
        f"/api/projects/{pid}/scenes/{scene_id}",
        json={"visual_description": "New visual", "duration": 5, "transition": "zoom"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["visual_description"] == "New visual"
    assert data["duration"] == 5
    assert data["transition"] == "zoom"

    async with async_session() as s:
        stored = (await s.execute(select(Scene).where(Scene.id == scene_id))).scalar_one_or_none()
    assert stored.visual_description == "New visual"
    assert stored.duration == 5


@pytest.mark.anyio
async def test_scene_patch_enforces_ownership(client: AsyncClient):
    token_a = await get_token(client, email="uxa@example.com")
    pid = await create_project(client, token_a)
    async with async_session() as s:
        scene = Scene(project_id=pid, scene_number=1, duration=3)
        s.add(scene)
        await s.commit()
        scene_id = str(scene.id)

    token_b = await get_token(client, email="uxb@example.com")
    assert (await client.patch(
        f"/api/projects/{pid}/scenes/{scene_id}",
        json={"visual_description": "x"},
        headers=auth_headers(token_b),
    )).status_code == 404

    assert (await client.patch(
        f"/api/projects/{pid}/scenes/00000000-0000-0000-0000-000000000000",
        json={"visual_description": "x"},
        headers=auth_headers(token_a),
    )).status_code == 404


@pytest.mark.anyio
async def test_agent_runs_returns_real_jobs_scoped_to_user(client: AsyncClient):
    token_a = await get_token(client, email="runsa@example.com")
    token_b = await get_token(client, email="runsb@example.com")
    pid_a = await create_project(client, token_a)
    pid_b = await create_project(client, token_b)

    async with async_session() as s:
        s.add(GenerationJob(project_id=pid_a, agent_name="script", status="completed",
                            model="gpt-4o", cost_cents=3, tokens_in=10, tokens_out=5))
        s.add(GenerationJob(project_id=pid_b, agent_name="storyboard", status="completed",
                            model="gpt-4o", cost_cents=9))
        await s.commit()

    resp_a = await client.get("/api/agents/runs", headers=auth_headers(token_a))
    resp_b = await client.get("/api/agents/runs", headers=auth_headers(token_b))

    data_a = resp_a.json()
    data_b = resp_b.json()
    assert data_a["total"] == 1
    assert data_a["runs"][0]["agent"] == "script"
    assert data_a["runs"][0]["cost_cents"] == 3
    assert data_b["total"] == 1
    assert data_b["runs"][0]["agent"] == "storyboard"