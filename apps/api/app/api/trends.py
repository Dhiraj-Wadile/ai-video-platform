from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trend import Trend, VideoAnalytics, AiInsight

router = APIRouter()


class TrendResponse(BaseModel):
    id: str
    topic: str
    source: Optional[str]
    score: Optional[float]
    metadata_json: Optional[dict]
    discovered_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[TrendResponse])
async def list_trends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()).limit(50))
    return result.scalars().all()


@router.post("/analyze")
async def analyze_trend(
    request: dict,
    user: User = Depends(get_current_user),
):
    from app.agents.registry import get_agent
    from app.providers.llm.openai import OpenAIProvider

    topic = request.get("topic", "")
    llm = OpenAIProvider()
    agent = get_agent("trend", llm)

    result = await agent.run({"content": topic})
    return result.structured_data
