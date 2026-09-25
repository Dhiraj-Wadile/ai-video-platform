from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import RenderJob
from app.services.pipeline import VideoPipeline
from app.tasks.render_tasks import render_project
from app.config import settings

router = APIRouter()


class RenderRequest(BaseModel):
    project_id: str
    topic: str
    duration: str = "30s"
    style: str = "educational"


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
            raise HTTPException(status_code=500, detail=job.error)

        return RenderResponse(
            status="queued",
            project_id=request.project_id,
            job_id=str(job.id),
            message="Render queued",
        )

    def on_progress(progress: float, message: str):
        job.progress = int(progress)
        job.progress_message = message

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
        raise HTTPException(status_code=500, detail=pipeline_result.error)

    job.status = "completed"
    job.progress = 100
    job.progress_message = "Pipeline complete!"
    job.output_url = pipeline_result.video_path
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
    result = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"job_id": job_id, "status": "unknown", "progress": 0}
    return {
        "job_id": str(job.id),
        "status": job.status or "unknown",
        "progress": job.progress or 0,
        "progress_message": job.progress_message,
        "error": job.error,
        "output_url": job.output_url,
    }
