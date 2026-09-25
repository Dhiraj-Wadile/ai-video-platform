import asyncio
import concurrent.futures


def run_async(coro):
    """Run an async coroutine from a sync context safely.

    If called while an event loop is running (e.g. nested from a Celery task
    invoked on a running loop), the coroutine runs in a worker thread.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=300)
    else:
        return asyncio.run(coro)