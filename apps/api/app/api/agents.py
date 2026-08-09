from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.agents.registry import get_agent, list_agents
from app.providers.llm.openai import OpenAIProvider

router = APIRouter()


class AgentRunRequest(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("")
async def list_available_agents(
    user: User = Depends(get_current_user),
):
    return {"agents": list_agents()}


@router.get("/runs")
async def get_agent_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"runs": [], "total": 0}


@router.post("/{agent_name}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    user: User = Depends(get_current_user),
):
    llm = OpenAIProvider()
    agent = get_agent(agent_name, llm)

    result = await agent.run({
        "content": request.content,
        "context": request.context or {},
    })

    return AgentRunResponse(
        content=result.content,
        structured_data=result.structured_data,
        metadata=result.metadata,
    )
