from celery import Celery
from app.config import settings

celery_app = Celery(
    "ai_video_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 min max per task
    task_soft_time_limit=1500,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

celery_app.autodiscover_tasks(["app.tasks"], related_name=None)

# autodiscover_tasks(related_name=None) only imports the listed packages themselves.
# The @shared_task definitions live in render_tasks / generation_tasks, so import them
# explicitly - otherwise the worker boots with zero app tasks and every .delay() call
# raises NotRegistered.
from app.tasks import generation_tasks, render_tasks  # noqa: E402,F401
