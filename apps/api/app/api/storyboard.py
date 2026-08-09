from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class StoryboardRequest(BaseModel):
    script: str
    characters: Optional[List[Dict[str, Any]]] = None
    style: str = "cinematic"


class StoryboardResponse(BaseModel):
    scenes: List[Dict[str, Any]]
    total_duration: float


@router.post("/generate", response_model=StoryboardResponse)
async def generate_storyboard(
    request: StoryboardRequest,
    user: User = Depends(get_current_user),
):
    from app.agents.registry import get_agent
    from app.providers.llm.openai import OpenAIProvider

    llm = OpenAIProvider()
    agent = get_agent("storyboard", llm)

    result = await agent.run({
        "content": request.script,
        "context": {
            "characters": request.characters or [],
            "style": request.style,
        }
    })

    data = result.structured_data or {}
    scenes = data.get("scenes", [])
    total_duration = sum(s.get("duration", 3) for s in scenes)

    return StoryboardResponse(
        scenes=scenes,
        total_duration=total_duration,
    )
