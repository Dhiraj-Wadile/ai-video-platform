from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.job import GenerationJob
from app.models.lineage import GenerationRecord

router = APIRouter()


@router.get("")
async def get_global_costs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = (await db.execute(
        select(Project).where(Project.user_id == user.id)
    )).scalars().all()
    project_ids = [p.id for p in projects]

    totals = {"cost_cents": 0, "latency_ms": 0, "calls": 0}
    per_project = []

    for pid in project_ids:
        jobs = (await db.execute(
            select(GenerationJob).where(GenerationJob.project_id == pid)
        )).scalars().all()
        records = (await db.execute(
            select(GenerationRecord).where(GenerationRecord.project_id == pid)
        )).scalars().all()

        cost = sum((j.cost_cents or 0) for j in jobs) + sum((r.cost_cents or 0) for r in records)
        latency = sum((j.latency_ms or 0) for j in jobs) + sum((r.latency_ms or 0) for r in records)
        calls = len(jobs) + len(records)

        totals["cost_cents"] += cost
        totals["latency_ms"] += latency
        totals["calls"] += calls
        per_project.append({
            "project_id": str(pid),
            "cost_cents": cost,
            "latency_ms": latency,
            "calls": calls,
        })

    per_project.sort(key=lambda p: p["cost_cents"], reverse=True)
    return {"totals": totals, "per_project": per_project}