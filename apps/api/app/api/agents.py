from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import GenerationJob
from app.agents.registry import get_agent, list_agents, AGENT_REGISTRY
from app.providers.base import ProviderTask
from app.providers.router import get_provider

router = APIRouter()


class AgentRunRequest(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    content: str
    # Agents legitimately return a list or scalar for some prompts; typing this as
    # Dict made any non-object model response a 500 at serialization time.
    structured_data: Optional[Any] = None
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
    project_ids = [p.id for p in (await db.execute(
        select(Project).where(Project.user_id == user.id)
    )).scalars().all()]

    runs = []
    if project_ids:
        # One query for every project instead of one per project; rows without a timestamp sort last.
        jobs = (await db.execute(
            select(GenerationJob)
            .where(GenerationJob.project_id.in_(project_ids))
            .order_by(GenerationJob.created_at.desc().nulls_last())
            .limit(200)
        )).scalars().all()
        runs = list(jobs)
    return {
        "runs": [
            {
                "id": str(r.id),
                "project_id": str(r.project_id),
                "agent": r.agent_name,
                "status": r.status,
                "model": r.model,
                "cost_cents": r.cost_cents,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "latency_ms": r.latency_ms,
                "error": r.error,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


@router.post("/{agent_name}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    user: User = Depends(get_current_user),
):
    # Resolve the name before the provider: a bad path is a client error even when
    # the deployment has no LLM key (otherwise this returned 503 instead of 404).
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    llm = get_provider(ProviderTask.LLM)
    try:
        agent = get_agent(agent_name, llm)
    except ValueError:
        # get_agent raises for an unregistered name; unhandled, that surfaced as a 500
        # for what is a bad request.
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    result = await agent.run({
        "content": request.content,
        "context": request.context or {},
    })

    return AgentRunResponse(
        content=result.content,
        structured_data=result.structured_data,
        metadata=result.metadata,
    )
