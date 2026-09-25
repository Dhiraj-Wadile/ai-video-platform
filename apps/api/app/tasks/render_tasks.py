from datetime import datetime, timezone

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async
from app.database import async_session
from app.models.job import RenderJob
from app.services.pipeline import VideoPipeline


@celery_app.task(bind=True, name="tasks.render_project")
def render_project(self, job_id: str, project_id: str, topic: str, duration: str, style: str):
    """Run the full video pipeline off the request thread and record live progress."""

    async def _run():
        async with async_session() as session:
            job = (
                await session.execute(select(RenderJob).where(RenderJob.id == job_id))
            ).scalar_one_or_none()
            if not job:
                return {"status": "not_found", "job_id": job_id}

            job.status = "rendering"
            await session.commit()

            async def on_progress(progress: float, message: str):
                job.progress = int(progress)
                job.progress_message = message
                await session.commit()

            pipeline = VideoPipeline()
            result = await pipeline.run(
                project_id=project_id,
                topic=topic,
                duration=duration,
                style=style,
                db=session,
                on_progress=on_progress,
            )

            if result.status == "failed":
                job.status = "failed"
                job.error = result.error
            else:
                job.status = "completed"
                job.progress = 100
                job.output_url = result.video_path
                job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return {"status": job.status, "job_id": job_id}

    return run_async(_run())