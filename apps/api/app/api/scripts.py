from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.script import Script, Scene
from app.agents.registry import get_agent
from app.providers.llm.openai import OpenAIProvider

router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    topic: str
    duration: str = "30s"
    style: str = "educational"
    additional_context: Optional[str] = None


class ScriptResponse(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    content: str
    duration: Optional[int] = None
    sections: Optional[dict] = None


@router.post("/generate", response_model=ScriptResponse)
async def generate_script(
    request: ScriptGenerateRequest,
    user: User = Depends(get_current_user),
):
    llm = OpenAIProvider()
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
    return ScriptResponse(
        title=data.get("title", request.topic),
        content=data.get("full_script", result.content),
        duration=data.get("duration"),
        sections=data.get("sections"),
    )


@router.get("/{script_id}")
async def get_script(
    script_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script
