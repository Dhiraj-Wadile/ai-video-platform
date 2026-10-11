from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.database import async_session
from app.models.job import RenderJob


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def token_for(client: AsyncClient, email: str) -> str:
    await client.post("/api/auth/register", json={
        "email": email, "name": "Bill User", "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def project_for(client: AsyncClient, token: str, name: str = "Bill project") -> str:
    resp = await client.post(
        "/api/projects", json={"name": name, "project_type": "short_form"}, headers=auth(token)
    )
    return resp.json()["id"]


@pytest.mark.anyio
async def test_plans_catalog_and_current_plan(client: AsyncClient):
    token = await token_for(client, "bill-plans@example.com")
    resp = await client.get("/api/billing/plans", headers=auth(token))
    assert resp.status_code == 200
    body = resp.json()
    ids = [p["id"] for p in body["plans"]]
    assert ids == ["free", "creator", "studio"]
    assert body["current_plan"] == "free"
    assert body["stripe_configured"] is False
    assert (await client.get("/api/billing/plans")).status_code == 401


@pytest.mark.anyio
async def test_new_user_starts_on_free_with_usage(client: AsyncClient):
    token = await token_for(client, "bill-usage@example.com")
    resp = await client.get("/api/billing/usage", headers=auth(token))
    assert resp.status_code == 200
    usage = resp.json()
    assert usage["plan"]["id"] == "free"
    assert usage["videos_used"] == 0
    assert usage["videos_limit"] == 3
    assert usage["videos_remaining"] == 3
    assert usage["unlimited"] is False


@pytest.mark.anyio
async def test_upgrade_in_demo_mode_changes_plan(client: AsyncClient):
    token = await token_for(client, "bill-upgrade@example.com")
    resp = await client.post("/api/billing/upgrade", json={"plan": "studio"}, headers=auth(token))
    assert resp.status_code == 200
    assert resp.json()["plan"] == "studio"

    me = await client.get("/api/auth/me", headers=auth(token))
    assert me.json()["plan"] == "studio"

    usage = await client.get("/api/billing/usage", headers=auth(token))
    assert usage.json()["unlimited"] is True


@pytest.mark.anyio
async def test_upgrade_rejects_unknown_plan(client: AsyncClient):
    token = await token_for(client, "bill-badplan@example.com")
    resp = await client.post("/api/billing/upgrade", json={"plan": "enterprise"}, headers=auth(token))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_checkout_demo_applies_plan(client: AsyncClient):
    token = await token_for(client, "bill-checkout@example.com")
    resp = await client.post(
        "/api/billing/checkout",
        json={"plan": "creator", "success_url": "http://localhost:3000/billing/success"},
        headers=auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "demo"
    assert body["applied"] is True

    me = await client.get("/api/auth/me", headers=auth(token))
    assert me.json()["plan"] == "creator"


@pytest.mark.anyio
async def test_checkout_rejects_free_plan(client: AsyncClient):
    token = await token_for(client, "bill-free-checkout@example.com")
    resp = await client.post("/api/billing/checkout", json={"plan": "free"}, headers=auth(token))
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_webhook_requires_configured_secret(client: AsyncClient):
    # No STRIPE_WEBHOOK_SECRET in tests -> the endpoint refuses rather than trusting payloads.
    resp = await client.post("/api/billing/webhook", json={"type": "checkout.session.completed"})
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_free_plan_video_limit_blocks_render_start(client: AsyncClient):
    token = await token_for(client, "bill-limit@example.com")
    pid = await project_for(client, token)

    # Simulate three renders already used this month.
    async with async_session() as s:
        for _ in range(3):
            s.add(RenderJob(project_id=pid, status="completed", progress=100))
        await s.commit()

    resp = await client.post(
        "/api/render/start",
        json={"project_id": pid, "topic": "a topic", "duration": "30s", "style": "educational"},
        headers=auth(token),
    )
    assert resp.status_code == 402
    assert "plan" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_paid_plan_is_not_blocked_by_free_limit(client: AsyncClient, monkeypatch):
    token = await token_for(client, "bill-paid@example.com")
    await client.post("/api/billing/upgrade", json={"plan": "creator"}, headers=auth(token))
    pid = await project_for(client, token)

    async with async_session() as s:
        for _ in range(3):
            s.add(RenderJob(project_id=pid, status="completed", progress=100))
        await s.commit()

    class FakeResult:
        status = "failed"
        error = "stubbed"
        project_id = pid
        video_url = None
        video_path = None

    class FakePipeline:
        async def run(self, **kwargs):
            return FakeResult()

    monkeypatch.setattr("app.api.render.VideoPipeline", FakePipeline)

    # Creator allows 30/month, so a 4th render passes the billing gate (the stubbed
    # pipeline then "fails", which is not the 402 we are guarding against).
    resp = await client.post(
        "/api/render/start",
        json={"project_id": pid, "topic": "a topic", "duration": "30s", "style": "educational"},
        headers=auth(token),
    )
    assert resp.status_code != 402
