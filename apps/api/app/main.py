from contextlib import asynccontextmanager
import logging
import mimetypes
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.database import engine
from app.api import auth, projects, scripts, characters, storyboard, assets, render, trends, analytics, agents, prompts, providers, costs, publishing, billing
from app.providers.base import ProviderNotConfigured, ProviderRequestError
from app.services.storage_service import (
    get_storage,
    verify_media_signature,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic (`alembic upgrade head`), never create_all.
    os.makedirs(settings.storage_dir, exist_ok=True)
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
app.include_router(providers.router, prefix="/api/providers", tags=["Providers"])
app.include_router(costs.router, prefix="/api/costs", tags=["Costs"])
app.include_router(publishing.router, prefix="/api/publishing", tags=["Publishing"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.exception_handler(ProviderNotConfigured)
async def provider_not_configured_handler(request: Request, exc: ProviderNotConfigured):
    # 503: the request was valid, the deployment is missing a key. Was an unhandled 500.
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "task": exc.task.value, "candidates": exc.candidates},
    )


@app.exception_handler(ProviderRequestError)
async def provider_request_error_handler(request: Request, exc: ProviderRequestError):
    # 502: an upstream we depend on failed. Was an unhandled 500.
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc), "provider": exc.provider},
    )


@app.exception_handler(httpx.HTTPError)
async def provider_transport_error_handler(request: Request, exc: httpx.HTTPError):
    # Any provider call we forgot to wrap still reports as a bad gateway, not a 500.
    logger.warning("Upstream HTTP failure on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=502, content={"detail": f"Upstream request failed: {exc}"})


# Media bytes are served through a signature check instead of a public StaticFiles mount.
# The mount made every rendered frame, scene image and narration world-readable to anyone
# who learned the URL, bypassing the ownership check on /api/assets/{key}; it also kept
# serving files after their project was deleted. URLs are signed (see sign_media_url)
# only after that ownership check passes, which keeps <img>/<video> working.
@app.get("/storage/{asset_key:path}")
async def get_media(
    asset_key: str,
    exp: str | None = None,
    sig: str | None = None,
):
    if not verify_media_signature(asset_key, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired media link")

    storage = get_storage()
    try:
        payload = await storage.read(asset_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Media not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media key")

    media_type, _ = mimetypes.guess_type(asset_key)
    return Response(content=payload, media_type=media_type or "application/octet-stream")
