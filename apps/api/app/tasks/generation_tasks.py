import asyncio
from app.tasks.celery_app import celery_app
from app.agents.registry import get_agent
from app.providers.llm.openai import OpenAIProvider


def _run_async(coro):
    """Run an async coroutine from a sync context safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=300)
    else:
        return asyncio.run(coro)


@celery_app.task(bind=True, name="tasks.analyze_trend")
def analyze_trend(self, topic: str, context: dict = None):
    """Analyze a trending topic for content potential."""
    llm = OpenAIProvider()
    agent = get_agent("trend", llm)
    result = _run_async(agent.run({"content": topic, "context": context or {}}))
    return {"status": "completed", "result": result.structured_data}


@celery_app.task(bind=True, name="tasks.generate_script")
def generate_script(self, topic: str, duration: str = "30s", style: str = "educational"):
    """Generate a video script."""
    llm = OpenAIProvider()
    agent = get_agent("script", llm)
    result = _run_async(agent.run({
        "content": topic,
        "context": {"duration": duration, "style": style}
    }))
    return {"status": "completed", "result": result.structured_data}


@celery_app.task(bind=True, name="tasks.generate_storyboard")
def generate_storyboard(self, script: str, characters: list = None):
    """Generate a storyboard from a script."""
    llm = OpenAIProvider()
    agent = get_agent("storyboard", llm)
    result = _run_async(agent.run({
        "content": script,
        "context": {"characters": characters or []}
    }))
    return {"status": "completed", "result": result.structured_data}


@celery_app.task(bind=True, name="tasks.quality_check")
def quality_check(self, content: str, context: dict = None):
    """Perform quality check on content."""
    llm = OpenAIProvider()
    agent = get_agent("quality", llm)
    result = _run_async(agent.run({
        "content": content,
        "context": context or {}
    }))
    return {"status": "completed", "result": result.structured_data}
