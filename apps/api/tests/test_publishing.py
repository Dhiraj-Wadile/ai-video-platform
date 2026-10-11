from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.database import async_session
from app.models.job import PublishingJob
from app.services.publishing_service import publish_due_jobs


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def token_for(client: AsyncClient, email: str) -> str:
    await client.post("/api/auth/register", json={
        "email": email, "name": "Pub User", "password": "testpass123",
    })
    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["access_token"]


async def project_for(client: AsyncClient, token: str, name: str = "Publish project") -> str:
    resp = await client.post(
        "/api/projects", json={"name": name, "project_type": "short_form"}, headers=auth(token)
    )
    return resp.json()["id"]


@pytest.mark.anyio
async def test_platforms_endpoint_lists_supported(client: AsyncClient):
    token = await token_for(client, "pub-platforms@example.com")
    resp = await client.get("/api/publishing/platforms", headers=auth(token))
    assert resp.status_code == 200
    platforms = {p["platform"] for p in resp.json()["platforms"]}
    assert platforms == {"youtube", "tiktok", "instagram"}
    # No keys configured in tests -> simulated mode.
    assert all(p["mode"] == "simulated" for p in resp.json()["platforms"])


@pytest.mark.anyio
async def test_immediate_publish_runs_in_request(client: AsyncClient):
    token = await token_for(client, "pub-now@example.com")
    pid = await project_for(client, token)

    resp = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["youtube", "tiktok"], "caption": "hello world"},
        headers=auth(token),
    )
    assert resp.status_code == 201, resp.text
    jobs = resp.json()
    assert len(jobs) == 2
    assert all(j["status"] == "published" for j in jobs)
    assert all(j["provider"] == "mock" for j in jobs)
    assert all(j["published_url"] for j in jobs)

    listed = await client.get(f"/api/publishing?project_id={pid}", headers=auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.anyio
async def test_future_publish_is_scheduled_and_picked_up(client: AsyncClient):
    token = await token_for(client, "pub-later@example.com")
    # Scheduling is a paid feature; upgrade first (demo mode: no Stripe key in tests).
    up = await client.post("/api/billing/upgrade", json={"plan": "creator"}, headers=auth(token))
    assert up.status_code == 200
    pid = await project_for(client, token)
    when = datetime.now(timezone.utc) + timedelta(minutes=5)

    resp = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["instagram"], "scheduled_at": when.isoformat()},
        headers=auth(token),
    )
    assert resp.status_code == 201
    job = resp.json()[0]
    assert job["status"] == "scheduled"

    # Bring the schedule forward and let the scheduler claim it.
    from sqlalchemy import update
    async with async_session() as s:
        await s.execute(
            update(PublishingJob)
            .where(PublishingJob.id == job["id"])
            .values(scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await s.commit()

    published = await publish_due_jobs()
    assert published == 1

    after = await client.get(f"/api/publishing?project_id={pid}", headers=auth(token))
    assert after.json()[0]["status"] == "published"


@pytest.mark.anyio
async def test_free_plan_cannot_schedule_future_post(client: AsyncClient):
    token = await token_for(client, "pub-free@example.com")
    pid = await project_for(client, token)
    when = datetime.now(timezone.utc) + timedelta(hours=2)
    resp = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["youtube"], "scheduled_at": when.isoformat()},
        headers=auth(token),
    )
    assert resp.status_code == 402

    # Immediate publish is still allowed on the free plan.
    now_resp = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["youtube"]},
        headers=auth(token),
    )
    assert now_resp.status_code == 201
    assert now_resp.json()[0]["status"] == "published"


@pytest.mark.anyio
async def test_unsupported_platform_rejected(client: AsyncClient):
    token = await token_for(client, "pub-bad@example.com")
    pid = await project_for(client, token)
    resp = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["myspace"]},
        headers=auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_publishing_jobs_are_scoped_to_owner(client: AsyncClient):
    token_a = await token_for(client, "pub-owner-a@example.com")
    token_b = await token_for(client, "pub-owner-b@example.com")
    pid_a = await project_for(client, token_a, "A")
    pid_b = await project_for(client, token_b, "B")

    created = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid_a, "platforms": ["youtube"]},
        headers=auth(token_a),
    )
    job_id = created.json()[0]["id"]

    # B cannot see A's project jobs, publish them, or cancel them.
    assert (await client.get(f"/api/publishing?project_id={pid_a}", headers=auth(token_b))).status_code == 404
    assert (await client.post(f"/api/publishing/jobs/{job_id}/publish", headers=auth(token_b))).status_code == 404
    assert (await client.delete(f"/api/publishing/jobs/{job_id}", headers=auth(token_b))).status_code == 404

    # Remaining unauthenticated access is rejected.
    assert (await client.get("/api/publishing")).status_code == 401
    _ = pid_b


@pytest.mark.anyio
async def test_cancel_only_scheduled_jobs(client: AsyncClient):
    token = await token_for(client, "pub-cancel@example.com")
    await client.post("/api/billing/upgrade", json={"plan": "creator"}, headers=auth(token))
    pid = await project_for(client, token)
    when = datetime.now(timezone.utc) + timedelta(hours=1)

    created = await client.post(
        "/api/publishing/schedule",
        json={"project_id": pid, "platforms": ["youtube"], "scheduled_at": when.isoformat()},
        headers=auth(token),
    )
    job_id = created.json()[0]["id"]

    cancelled = await client.post(f"/api/publishing/jobs/{job_id}/cancel", headers=auth(token))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # A second cancel (already cancelled) is a conflict.
    again = await client.post(f"/api/publishing/jobs/{job_id}/cancel", headers=auth(token))
    assert again.status_code == 409
