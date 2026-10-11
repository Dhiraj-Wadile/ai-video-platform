from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.llm_output import as_dict, coerce_float
from app.core.security import get_current_user
from app.models.user import User
from app.providers.base import ProviderTask
from app.providers.router import get_provider

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

    # Via the router, not OpenAIProvider(): constructing it directly raised a raw
    # OpenAIError when OPENAI_API_KEY was unset, which surfaced as a 500.
    llm = get_provider(ProviderTask.LLM)
    agent = get_agent("storyboard", llm)

    result = await agent.run({
        "content": request.script,
        "context": {
            "characters": request.characters or [],
            "style": request.style,
        }
    })

    data = as_dict(result.structured_data)
    scenes = data.get("scenes") or []
    # Models return durations as 3, "3", "3.5" or "3-4s"; a raw sum raised TypeError
    # on anything but a number.
    total_duration = sum(coerce_float(s.get("duration"), 3.0) or 0.0 for s in scenes)

    return StoryboardResponse(
        scenes=scenes,
        total_duration=total_duration,
    )
