from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trend import Trend

router = APIRouter()


class TrendResponse(BaseModel):
    id: str
    topic: str
    source: Optional[str]
    score: Optional[float]
    metadata_json: Optional[dict]
    discovered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("discovered_at")
    def serialize_discovered_at(self, v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if isinstance(v, datetime) else v


class TrendAnalyzeRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)


@router.get("", response_model=List[TrendResponse])
async def list_trends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()).limit(50))
    return result.scalars().all()


@router.post("/analyze")
async def analyze_trend(
    request: TrendAnalyzeRequest,
    user: User = Depends(get_current_user),
):
    from app.agents.registry import get_agent

    from app.providers.base import ProviderTask
    from app.providers.router import get_provider

    llm = get_provider(ProviderTask.LLM)
    agent = get_agent("trend", llm)

    result = await agent.run({"content": request.topic})
    if not result.structured_data:
        raise HTTPException(status_code=502, detail="Trend analysis returned no data")
    return result.structured_data
