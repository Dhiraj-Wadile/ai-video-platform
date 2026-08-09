from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api import auth, projects, scripts, characters, storyboard, assets, render, trends, analytics, agents, prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Video Platform API",
    description="AI-powered video automation platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["Scripts"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
app.include_router(storyboard.router, prefix="/api/storyboard", tags=["Storyboard"])
app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(render.router, prefix="/api/render", tags=["Render"])
app.include_router(trends.router, prefix="/api/trends", tags=["Trends"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
