from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import RenderJob
from app.services.pipeline import VideoPipeline

router = APIRouter()


class RenderRequest(BaseModel):
    project_id: str
    topic: str
    duration: str = "30s"
    style: str = "educational"


class RenderResponse(BaseModel):
    status: str
    project_id: str
    message: str


@router.post("/start", response_model=RenderResponse)
async def start_render(
    request: RenderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pipeline = VideoPipeline()
    pipeline_result = await pipeline.run(
        project_id=request.project_id,
        topic=request.topic,
        duration=request.duration,
        style=request.style,
    )

    if pipeline_result.status == "failed":
        raise HTTPException(status_code=500, detail=pipeline_result.error)

    return RenderResponse(
        status=pipeline_result.status,
        project_id=pipeline_result.project_id,
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
        "status": job.status.value if job.status else "unknown",
        "progress": job.progress or 0,
        "output_url": job.output_url,
    }
