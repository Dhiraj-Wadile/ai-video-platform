from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trend import VideoAnalytics, AiInsight

router = APIRouter()


@router.get("")
async def get_analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VideoAnalytics).order_by(VideoAnalytics.fetched_at.desc()).limit(100))
    analytics = result.scalars().all()

    total_views = sum(a.views or 0 for a in analytics)
    total_likes = sum(a.likes or 0 for a in analytics)
    total_comments = sum(a.comments or 0 for a in analytics)
    total_shares = sum(a.shares or 0 for a in analytics)

    return {
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "video_count": len(analytics),
        "engagement_rate": round((total_likes + total_comments + total_shares) / max(total_views, 1) * 100, 2),
    }


@router.get("/{project_id}")
async def get_video_analytics(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VideoAnalytics).where(VideoAnalytics.project_id == project_id)
    )
    return result.scalars().all()
