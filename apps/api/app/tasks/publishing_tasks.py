from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async


@celery_app.task(name="tasks.publish_due")
def publish_due():
    """Publish every scheduled job whose time has arrived (run by Celery beat)."""
    from app.services.publishing_service import publish_due_jobs

    async def _run():
        count = await publish_due_jobs()
        return {"published": count}

    return run_async(_run())
