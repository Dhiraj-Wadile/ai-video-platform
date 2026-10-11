from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _engine_kwargs(url: str) -> dict:
    """Pool sizing only applies to dialects that queue connections.

    SQLite uses StaticPool (in-memory) or NullPool depending on the target, and both
    reject pool_size/max_overflow. Passing them unconditionally made the engine
    unconstructable for :memory: URLs.
    """
    if url.startswith("sqlite"):
        return {}
    return {"pool_size": 20, "max_overflow": 10}


engine = create_async_engine(
    settings.database_url, echo=False, **_engine_kwargs(settings.database_url)
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
