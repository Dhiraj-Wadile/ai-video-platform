from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import PublishingJob
from app.api.deps import owned_project_or_404
from app.services.publishing_service import (
    SUPPORTED_PLATFORMS,
    platform_status,
    publish_job,
)
from app.services import billing_service

router = APIRouter()

CANCELLABLE = {"scheduled", "queued"}
PUBLISHABLE = {"scheduled", "queued", "failed"}


class PublishingJobResponse(BaseModel):
    id: str
    project_id: str
    platform: str
    status: str
    title: Optional[str] = None
    caption: Optional[str] = None
    provider: Optional[str] = None
    external_id: Optional[str] = None
    published_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleRequest(BaseModel):
    project_id: str
    platforms: List[str] = Field(..., min_length=1, max_length=4)
    scheduled_at: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=255)
    caption: Optional[str] = Field(None, max_length=5000)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _owned_job_or_404(db: AsyncSession, job_id: str, user: User) -> PublishingJob:
    job = (
        await db.execute(select(PublishingJob).where(PublishingJob.id == job_id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publishing job not found")
    # Ownership lives on the project; another user's job must look like it does not exist.
    await owned_project_or_404(db, str(job.project_id), user)
    return job


@router.get("/platforms")
async def list_platforms(user: User = Depends(get_current_user)):
    return {"platforms": platform_status()}


@router.get("", response_model=List[PublishingJobResponse])
async def list_jobs(
    project_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project_ids = [
        row[0]
        for row in (
            await db.execute(select(Project.id).where(Project.user_id == user.id))
        ).all()
    ]
    if project_id:
        if project_id not in [str(p) for p in project_ids]:
            raise HTTPException(status_code=404, detail="Project not found")
        project_ids = [project_id]

    result = await db.execute(
        select(PublishingJob)
        .where(PublishingJob.project_id.in_(project_ids))
        .order_by(PublishingJob.created_at.desc())
    )
    return result.scalars().all()


@router.post("/schedule", response_model=List[PublishingJobResponse], status_code=201)
async def schedule_publish(
    request: ScheduleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await owned_project_or_404(db, request.project_id, user)

    invalid = [p for p in request.platforms if p not in SUPPORTED_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported platform(s): {', '.join(invalid)}. Choose from {', '.join(SUPPORTED_PLATFORMS)}.",
        )

    when = _as_utc(request.scheduled_at)
    now = datetime.now(timezone.utc)
    title = request.title or project.name
    caption = request.caption or project.description or ""

    # Future-dated posts are a paid feature; immediate publishing is available to everyone.
    if when is not None and when > now and not await billing_service.plan_allows_scheduling(user):
        raise HTTPException(
            status_code=402,
            detail="Scheduling posts for later is available on paid plans. Upgrade to unlock it, or publish now.",
        )

    jobs: List[PublishingJob] = []
    for platform in dict.fromkeys(request.platforms):  # de-dupe, keep order
        immediate = when is None or when <= now
        job = PublishingJob(
            project_id=request.project_id,
            platform=platform,
            status="queued" if immediate else "scheduled",
            title=title,
            caption=caption,
            scheduled_at=when,
        )
        db.add(job)
        jobs.append(job)

    await db.flush()

    # Immediate publishes run in-request; future ones are picked up by the scheduler.
    for job in jobs:
        if job.status == "queued":
            await publish_job(db, job)

    if any(j.status == "published" for j in jobs):
        project.status = "published"
    elif any(j.status == "scheduled" for j in jobs):
        project.status = "scheduled"

    await db.commit()
    return jobs


@router.post("/jobs/{job_id}/publish", response_model=PublishingJobResponse)
async def publish_now(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _owned_job_or_404(db, job_id, user)
    if job.status not in PUBLISHABLE:
        raise HTTPException(status_code=409, detail=f"Job is already {job.status}")
    await publish_job(db, job)
    await db.commit()
    return job


@router.post("/jobs/{job_id}/cancel", response_model=PublishingJobResponse)
async def cancel_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _owned_job_or_404(db, job_id, user)
    if job.status not in CANCELLABLE:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a {job.status} job")
    job.status = "cancelled"
    await db.flush()
    await db.commit()
    return job


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _owned_job_or_404(db, job_id, user)
    await db.delete(job)
    await db.commit()
