import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["JWT_SECRET"] = "test-secret-key"

from app.main import app
from app.database import engine, Base
from app.models import *  # noqa - ensure all models are loaded


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
