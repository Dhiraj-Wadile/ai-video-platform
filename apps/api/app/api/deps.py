from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User


async def owned_project_or_404(db: AsyncSession, project_id: str, user: User) -> Project:
    """Fetch a project the caller owns, or 404.

    A 404 (rather than 403) is deliberate: it does not confirm that someone else's project exists.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def owned_project_ids(db: AsyncSession, user: User) -> list:
    rows = (await db.execute(
        select(Project.id).where(Project.user_id == user.id)
    )).all()
    return [row[0] for row in rows]


def project_id_from_asset_key(asset_key: str) -> Optional[str]:
    """Extract the project id from an asset key shaped ``projects/{project_id}/{type}/{file}``.

    Keys are produced by ``storage_service.generate_asset_key``. Anything else is not addressable.
    """
    parts = asset_key.split("/")
    if len(parts) < 4 or parts[0] != "projects" or not parts[1]:
        return None
    return parts[1]
