import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_register(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.anyio
async def test_register_duplicate(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "name": "Dup User",
        "password": "testpassword123",
    })
    response = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "name": "Dup User 2",
        "password": "testpassword123",
    })
    assert response.status_code == 400


@pytest.mark.anyio
async def test_login(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "name": "Login User",
        "password": "mypassword",
    })
    response = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "wrong@example.com",
        "name": "Wrong User",
        "password": "correctpass",
    })
    response = await client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpass",
    })
    assert response.status_code == 401
