import pytest
from httpx import AsyncClient


async def get_token(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "email": "project@example.com",
        "name": "Project User",
        "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "project@example.com",
        "password": "testpass123",
    })
    return resp.json()["access_token"]


@pytest.mark.anyio
async def test_create_project(client: AsyncClient):
    token = await get_token(client)
    response = await client.post("/api/projects", json={
        "name": "My First Video",
        "description": "A test video",
        "project_type": "short_form",
        "platform": "youtube_shorts",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My First Video"
    assert data["status"] == "draft"


@pytest.mark.anyio
async def test_list_projects(client: AsyncClient):
    token = await get_token(client)
    await client.post("/api/projects", json={
        "name": "Project A",
        "project_type": "short_form",
    }, headers={"Authorization": f"Bearer {token}"})
    response = await client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.anyio
async def test_projects_requires_auth(client: AsyncClient):
    response = await client.get("/api/projects")
    assert response.status_code in (401, 403)
