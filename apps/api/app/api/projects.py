from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import os

from app.config import settings
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.script import Script, Scene
from app.models.asset import Asset
from app.models.job import GenerationJob
from app.models.quality import QualityReview
from app.models.lineage import GenerationRecord
from app.services.quality_service import QualityGate, _gate_passed
from app.services.storage_service import get_storage, generate_asset_key, sign_media_url
from app.services.pipeline import materialise_image
from app.providers.router import provider_router
from app.providers.base import ProviderTask
from app.api.deps import owned_project_or_404

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=20_000)
    project_type: str = Field("short_form", max_length=50)
    platform: Optional[str] = Field(None, max_length=50)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=20_000)
    status: Optional[str] = Field(None, max_length=30)
    platform: Optional[str] = Field(None, max_length=50)

    @field_validator("status")
    @classmethod
    def known_status(cls, v):
        if v is not None and v not in {s.value for s in ProjectStatus}:
            raise ValueError(f"status must be one of {sorted(s.value for s in ProjectStatus)}")
        return v


class SceneUpdate(BaseModel):
    duration: Optional[int] = Field(None, ge=1, le=120)
    narration: Optional[str] = Field(None, max_length=10_000)
    visual_description: Optional[str] = Field(None, max_length=10_000)
    camera: Optional[str] = Field(None, max_length=200)
    emotion: Optional[str] = Field(None, max_length=200)
    background: Optional[str] = Field(None, max_length=2_000)
    music_mood: Optional[str] = Field(None, max_length=200)
    sfx: Optional[str] = Field(None, max_length=200)
    caption: Optional[str] = Field(None, max_length=2_000)
    transition: Optional[str] = Field(None, max_length=50)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    status: str
    project_type: str
    platform: Optional[str]
    created_at: Any

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return projects


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        user_id=user.id,
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        platform=request.platform,
    )
    db.add(project)
    await db.flush()
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        if not hasattr(Project, field):
            raise HTTPException(status_code=422, detail=f"Unknown field '{field}'")
        if value is None and getattr(Project, field).nullable is False:
            raise HTTPException(status_code=422, detail=f"Field '{field}' cannot be null")
        setattr(project, field, value)

    await db.flush()
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    return {"status": "deleted"}


async def _owned_project(db: AsyncSession, project_id: str, user: User) -> Project:
    return await owned_project_or_404(db, project_id, user)


def _review_dict(review: Optional[QualityReview]) -> Optional[dict]:
    if review is None:
        return None
    return {
        "id": str(review.id),
        "overall_score": review.overall_score,
        "breakdown": review.breakdown_json,
        "problems": review.problems_json,
        "recommendations": review.recommendations_json,
        "safe_to_publish": review.safe_to_publish,
        "source": review.source,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "passed": _gate_passed(review),
    }


@router.get("/{project_id}/quality")
async def get_project_quality(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)
    review = await QualityGate.latest(db, project_id)
    return {"project_id": project_id, "review": _review_dict(review)}


class QualityReviewRequest(BaseModel):
    script: Optional[str] = None
    # Name of a registered LLM provider. Was typed Any, which let a client install an
    # arbitrary JSON value as the provider object and crash the request.
    llm_provider: Optional[str] = None


@router.post("/{project_id}/quality/review")
async def review_project_quality(
    project_id: str,
    request: QualityReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)

    script_row = None
    if request.script is None:
        script_result = await db.execute(
            select(Script).where(Script.project_id == project_id).order_by(Script.created_at.desc()).limit(1)
        )
        script_row = script_result.scalar_one_or_none()

    scenes_result = await db.execute(
        select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_number.asc())
    )
    scenes = scenes_result.scalars().all()
    scenes_data = [
        {
            "scene_number": s.scene_number,
            "narration": s.narration,
            "visual_description": s.visual_description,
            "caption": s.caption,
            "camera": s.camera,
            "emotion": s.emotion,
        }
        for s in scenes
    ]

    script_content = request.script or (script_row.content if script_row else "")
    if not script_content:
        raise HTTPException(status_code=400, detail="No script available to review; provide one in the request")

    gate = QualityGate(llm_provider_name=request.llm_provider)
    review = await gate.review(project_id, script_content, scenes_data, db, source="manual")
    await db.commit()
    return {"project_id": project_id, "review": _review_dict(review)}


@router.get("/{project_id}/costs")
async def get_project_costs(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)

    jobs = (await db.execute(
        select(GenerationJob).where(GenerationJob.project_id == project_id)
    )).scalars().all()
    records = (await db.execute(
        select(GenerationRecord).where(GenerationRecord.project_id == project_id)
    )).scalars().all()

    agent_breakdown: dict = {}
    for j in jobs:
        entry = agent_breakdown.setdefault(j.agent_name or "unknown", {"calls": 0, "cost_cents": 0, "latency_ms": 0, "tokens_in": 0, "tokens_out": 0})
        entry["calls"] += 1
        entry["cost_cents"] += j.cost_cents or 0
        entry["latency_ms"] += j.latency_ms or 0
        entry["tokens_in"] += j.tokens_in or 0
        entry["tokens_out"] += j.tokens_out or 0

    task_breakdown: dict = {}
    for r in records:
        entry = task_breakdown.setdefault(r.task or "unknown", {"calls": 0, "cost_cents": 0, "latency_ms": 0})
        entry["calls"] += 1
        entry["cost_cents"] += r.cost_cents or 0
        entry["latency_ms"] += r.latency_ms or 0

    total_cost = sum(j.cost_cents or 0 for j in jobs) + sum(r.cost_cents or 0 for r in records)
    total_latency = sum(j.latency_ms or 0 for j in jobs) + sum(r.latency_ms or 0 for r in records)

    return {
        "project_id": project_id,
        "total_cost_cents": total_cost,
        "total_latency_ms": total_latency,
        "agent_breakdown": agent_breakdown,
        "task_breakdown": task_breakdown,
    }


@router.get("/{project_id}/lineage")
async def get_project_lineage(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)
    records = (await db.execute(
        select(GenerationRecord)
        .where(GenerationRecord.project_id == project_id)
        .order_by(GenerationRecord.created_at.desc())
    )).scalars().all()
    return {
        "project_id": project_id,
        "records": [
            {
                "id": str(r.id),
                "task": r.task,
                "provider": r.provider,
                "model": r.model,
                "status": r.status,
                "cost_cents": r.cost_cents,
                "latency_ms": r.latency_ms,
                "parent_id": r.parent_id,
                "context": r.context_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/{project_id}/detail")
async def get_project_detail(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, project_id, user)

    script_row = (await db.execute(
        select(Script).where(Script.project_id == project_id).order_by(Script.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    scenes = (await db.execute(
        select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_number.asc())
    )).scalars().all()

    assets = (await db.execute(
        select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())
    )).scalars().all()

    image_by_scene: dict = {}
    for a in assets:
        if a.type == "scene_image":
            sid = (a.metadata_json or {}).get("scene_id")
            if sid is not None and sid not in image_by_scene:
                # Signed on the way out: the stored URL is a bare key, the browser gets a
                # short-lived link it can only have obtained via an ownership check.
                image_by_scene[int(sid)] = sign_media_url(a.url)

    video_assets = [a for a in assets if a.type == "video"]

    review = await QualityGate.latest(db, project_id)

    return {
        "id": str(project.id),
        "name": project.name,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "script": {
            "id": str(script_row.id) if script_row else None,
            "title": script_row.title if script_row else None,
            "content": script_row.content if script_row else None,
        },
        "scenes": [
            {
                "id": str(s.id),
                "scene_number": s.scene_number,
                "duration": s.duration,
                "narration": s.narration,
                "visual_description": s.visual_description,
                "camera": s.camera,
                "emotion": s.emotion,
                "caption": s.caption,
                "transition": s.transition,
                "image_url": image_by_scene.get(s.scene_number),
            }
            for s in scenes
        ],
        "video_url": sign_media_url(video_assets[0].url) if video_assets else None,
        "quality": _review_dict(review),
    }


@router.patch("/{project_id}/scenes/{scene_id}")
async def update_scene(
    project_id: str,
    scene_id: str,
    request: SceneUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)
    scene_result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.project_id == project_id)
    )
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        if not hasattr(Scene, field):
            raise HTTPException(status_code=422, detail=f"Unknown field '{field}'")
        setattr(scene, field, value)
    await db.commit()
    return {
        "id": str(scene.id),
        "scene_number": scene.scene_number,
        "duration": scene.duration,
        "narration": scene.narration,
        "visual_description": scene.visual_description,
        "camera": scene.camera,
        "emotion": scene.emotion,
        "background": scene.background,
        "music_mood": scene.music_mood,
        "sfx": scene.sfx,
        "caption": scene.caption,
        "transition": scene.transition,
    }


@router.post("/{project_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene_visual(
    project_id: str,
    scene_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_project(db, project_id, user)

    scene_result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.project_id == project_id)
    )
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    image = provider_router.resolve(ProviderTask.IMAGE)
    prompt = scene.visual_description or scene.narration or f"Scene {scene.scene_number}"
    images = await image.generate(prompt=f"Cinematic, high quality: {prompt}", size="1080x1920")
    # An empty url used to fall through to a zero-byte upload reported as success.
    if not images or not images[0].url:
        raise HTTPException(status_code=502, detail="Image provider returned no results")
    image_url = images[0].url

    storage = get_storage()
    key = generate_asset_key(project_id, "scene_image", "png")
    tmp_path = os.path.join(
        settings.storage_dir, "projects", str(project_id), "scene", f"regen_{scene.id}.png"
    )
    try:
        await materialise_image(storage, image_url, tmp_path)
        with open(tmp_path, "rb") as f:
            await storage.upload(f.read(), key, "image/png")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Store the stable key; the response gets a freshly signed url.
    stored_url = await storage.get_url(key)
    asset_url = sign_media_url(stored_url)

    db.add(Asset(
        project_id=project_id,
        type="scene_image",
        url=stored_url,
        metadata_json={
            "scene_id": scene.scene_number,
            "source": "regenerate",
            "regenerated": True,
            "key": key,
        },
    ))

    latest_image_records = (await db.execute(
        select(GenerationRecord).where(
            GenerationRecord.project_id == project_id,
            GenerationRecord.task == "image",
        ).order_by(GenerationRecord.created_at.desc())
    )).scalars().all()
    parent = next((r for r in latest_image_records if (r.context_json or {}).get("scene_id") == scene.scene_number), None)

    record = GenerationRecord(
        project_id=project_id,
        task="image",
        provider=getattr(image, "name", type(image).__name__),
        model=getattr(image, "default_model", None),
        status="completed",
        cost_cents=0,
        latency_ms=0,
        parent_id=str(parent.id) if parent else None,
        context_json={"scene_id": scene.scene_number, "source": "regenerate", "key": key},
    )
    db.add(record)
    await db.commit()

    return {
        "scene_id": str(scene.id),
        "scene_number": scene.scene_number,
        "asset_url": asset_url,
        "record_id": str(record.id),
        "parent_record_id": record.parent_id,
    }
