from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.llm_output import coerce_int
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.script import Script
from app.models.project import Project
from app.agents.registry import get_agent
from app.providers.base import ProviderTask
from app.providers.router import get_provider

router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    topic: str
    duration: str = "30s"
    style: str = "educational"
    additional_context: Optional[str] = None
    project_id: Optional[str] = None


class ScriptResponse(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    content: str
    duration: Optional[int] = None
    # The prompt asks for an object but models routinely return a list of section
    # dicts; the column is JSON so either round-trips, and typing it as dict made a
    # valid response a 500.
    sections: Optional[Any] = None


@router.post("/generate", response_model=ScriptResponse)
async def generate_script(
    request: ScriptGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    llm = get_provider(ProviderTask.LLM)
    agent = get_agent("script", llm)

    result = await agent.run({
        "content": request.topic,
        "context": {
            "duration": request.duration,
            "style": request.style,
            "additional_context": request.additional_context or "",
        }
    })

    data = result.structured_data or {}
    # "30s" / "30 seconds" are as likely as 30; the column is an integer.
    duration = coerce_int(data.get("duration"))
    body = data.get("full_script") or result.content or ""
    title = data.get("title") or request.topic

    script_id = None
    if request.project_id:
        project_check = await db.execute(
            select(Project).where(Project.id == request.project_id, Project.user_id == user.id)
        )
        project = project_check.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        script = Script(
            project_id=request.project_id,
            title=title,
            content=body,
            duration=duration,
            structure_json=data.get("sections"),
        )
        db.add(script)
        await db.flush()
        script_id = str(script.id)
        project.status = "generating"

    return ScriptResponse(
        id=script_id,
        title=title,
        content=body,
        duration=duration,
        sections=data.get("sections"),
    )


@router.get("/{script_id}")
async def get_script(
    script_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Script)
        .join(Project, Project.id == Script.project_id)
        .where(Script.id == script_id, Project.user_id == user.id)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script
