from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.trend import VideoAnalytics
from app.api.deps import owned_project_ids, owned_project_or_404

router = APIRouter()


def _engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    return round((likes + comments + shares) / max(views, 1) * 100, 2)


@router.get("")
async def get_analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project_ids = await owned_project_ids(db, user)
    if not project_ids:
        return {
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "video_count": 0,
            "engagement_rate": 0.0,
            "videos": [],
        }

    projects = {p.id: p for p in (await db.execute(
        select(Project).where(Project.id.in_(project_ids))
    )).scalars().all()}

    # `video_analytics` is a snapshot table: one row per (project, platform) per fetch. Summing every
    # row would add yesterday's numbers to today's, so only the newest snapshot per video counts.
    platform_key = func.coalesce(VideoAnalytics.platform, "")
    latest = (
        select(
            VideoAnalytics.project_id.label("project_id"),
            platform_key.label("platform_key"),
            func.max(VideoAnalytics.fetched_at).label("fetched_at"),
        )
        .where(VideoAnalytics.project_id.in_(project_ids))
        .group_by(VideoAnalytics.project_id, platform_key)
        .subquery()
    )
    analytics = (await db.execute(
        select(VideoAnalytics)
        .join(
            latest,
            (VideoAnalytics.project_id == latest.c.project_id)
            & (platform_key == latest.c.platform_key)
            & (VideoAnalytics.fetched_at == latest.c.fetched_at),
        )
    )).scalars().all()

    total_views = sum(a.views or 0 for a in analytics)
    total_likes = sum(a.likes or 0 for a in analytics)
    total_comments = sum(a.comments or 0 for a in analytics)
    total_shares = sum(a.shares or 0 for a in analytics)

    videos = [
        {
            "project_id": str(a.project_id),
            "title": projects[a.project_id].name if a.project_id in projects else "Untitled",
            "platform": projects[a.project_id].platform if a.project_id in projects else None,
            "views": a.views or 0,
            "likes": a.likes or 0,
            "comments": a.comments or 0,
            "shares": a.shares or 0,
            "engagement_rate": _engagement_rate(a.views or 0, a.likes or 0, a.comments or 0, a.shares or 0),
            "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None,
        }
        for a in analytics
    ]
    videos.sort(key=lambda v: v["views"], reverse=True)

    return {
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "video_count": len(analytics),
        "engagement_rate": _engagement_rate(total_views, total_likes, total_comments, total_shares),
        "videos": videos,
    }


@router.get("/{project_id}")
async def get_video_analytics(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await owned_project_or_404(db, project_id, user)

    result = await db.execute(
        select(VideoAnalytics)
        .where(VideoAnalytics.project_id == project_id)
        .order_by(VideoAnalytics.fetched_at.desc())
    )
    return result.scalars().all()

