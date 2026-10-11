from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import RenderJob
from app.services.pipeline import VideoPipeline
from app.services.storage_service import sign_media_url
from app.services import billing_service
from app.tasks.render_tasks import render_project
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class RenderRequest(BaseModel):
    project_id: str
    topic: str = Field(..., min_length=1, max_length=500)
    duration: str = Field("30s", max_length=20)
    style: str = Field("educational", max_length=50)


class RenderResponse(BaseModel):
    status: str
    project_id: str
    job_id: str
    message: str


@router.post("/start", response_model=RenderResponse)
async def start_render(
    request: RenderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == request.project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Enforce the monthly video allowance for the caller's plan. 402 = payment required.
    if not await billing_service.plan_allows_video(db, user):
        usage = await billing_service.usage_summary(db, user)
        raise HTTPException(
            status_code=402,
            detail=(
                f"You've used all {usage['videos_limit']} videos on the "
                f"{usage['plan']['name']} plan this month. Upgrade your plan to keep creating."
            ),
        )

    job = RenderJob(project_id=request.project_id, status="queued", progress=0)
    db.add(job)
    await db.commit()

    if settings.render_async:
        try:
            render_project.delay(
                job_id=str(job.id),
                project_id=request.project_id,
                topic=request.topic,
                duration=request.duration,
                style=request.style,
            )
        except Exception as e:
            job.status = "failed"
            job.error = f"Failed to enqueue render: {e}"
            await db.commit()
            logger.exception("Could not enqueue render for project %s", request.project_id)
            raise HTTPException(status_code=500, detail="Could not queue the render job")

        return RenderResponse(
            status="queued",
            project_id=request.project_id,
            job_id=str(job.id),
            message="Render queued",
        )

    async def on_progress(progress: float, message: str):
        # Commit each step: /status is polled from a different session, so an in-memory
        # mutation is invisible until the render finishes and progress sat at 0 throughout.
        job.progress = int(progress)
        job.progress_message = message
        await db.commit()

    job.status = "rendering"
    await db.commit()

    pipeline = VideoPipeline()
    pipeline_result = await pipeline.run(
        project_id=request.project_id,
        topic=request.topic,
        duration=request.duration,
        style=request.style,
        db=db,
        on_progress=on_progress,
    )

    if pipeline_result.status == "failed":
        job.status = "failed"
        job.error = pipeline_result.error
        await db.commit()
        # The stored error keeps the ffmpeg/provider detail for the Runs screen; the HTTP response
        # does not, so internal paths and stderr never reach an unauthenticated reader.
        # logger.exception outside an except block logs "NoneType: None" and drops the traceback.
        logger.error("Render failed for project %s: %s", request.project_id, pipeline_result.error)
        raise HTTPException(status_code=500, detail="Render failed. See the render job for details.")

    job.status = "completed"
    job.progress = 100
    job.progress_message = "Pipeline complete!"
    # A filesystem path is not a URL and leaked the server's directory layout; the pipeline
    # already uploads the finished video to storage, so use the URL it minted.
    job.output_url = pipeline_result.video_url or pipeline_result.video_path
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return RenderResponse(
        status=pipeline_result.status,
        project_id=pipeline_result.project_id,
        job_id=str(job.id),
        message="Render completed successfully",
    )


@router.get("/status/{job_id}")
async def get_render_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RenderJob)
        .join(Project, Project.id == RenderJob.project_id)
        .where(RenderJob.id == job_id, Project.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return {
        "job_id": str(job.id),
        "status": job.status or "unknown",
        "progress": job.progress or 0,
        "progress_message": job.progress_message,
        "error": job.error,
        "output_url": sign_media_url(job.output_url) if job.output_url else None,
    }


class RecutRequest(BaseModel):
    project_id: str


@router.post("/recut", response_model=RenderResponse)
async def recut_render(
    request: RecutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.recut_service import RecutService

    project_result = await db.execute(
        select(Project).where(Project.id == request.project_id, Project.user_id == user.id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        job = await RecutService().recut(request.project_id, db)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await db.rollback()
        logger.exception("Re-cut failed for project %s", request.project_id)
        raise HTTPException(status_code=500, detail="Re-cut failed. See the render job for details.")

    return RenderResponse(
        status="completed",
        project_id=request.project_id,
        job_id=str(job.id),
        message="Re-render completed successfully",
    )
