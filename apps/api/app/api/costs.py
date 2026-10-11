from fastapi import APIRouter, Depends
from sqlalchemy import func, select
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
    project_ids = [p.id for p in (await db.execute(
        select(Project).where(Project.user_id == user.id)
    )).scalars().all()]

    totals = {"cost_cents": 0, "latency_ms": 0, "calls": 0}
    per_project = []
    if not project_ids:
        return {"totals": totals, "per_project": per_project}

    # Two grouped queries in total. The previous version issued one query per project per
    # table, so the page cost 2N+1 round trips.
    async def aggregate(model):
        return (await db.execute(
            select(
                model.project_id,
                func.coalesce(func.sum(model.cost_cents), 0),
                func.coalesce(func.sum(model.latency_ms), 0),
                func.count(model.id),
            )
            .where(model.project_id.in_(project_ids))
            .group_by(model.project_id)
        )).all()

    combined: dict = {}
    for pid, cost, latency, calls in await aggregate(GenerationJob):
        combined.setdefault(str(pid), {"cost_cents": 0, "latency_ms": 0, "calls": 0})
        combined[str(pid)].update(cost_cents=int(cost), latency_ms=int(latency), calls=int(calls))
    for pid, cost, latency, calls in await aggregate(GenerationRecord):
        combined.setdefault(str(pid), {"cost_cents": 0, "latency_ms": 0, "calls": 0})
        entry = combined[str(pid)]
        entry["cost_cents"] += int(cost)
        entry["latency_ms"] += int(latency)
        entry["calls"] += int(calls)

    for pid, agg in combined.items():
        totals["cost_cents"] += agg["cost_cents"]
        totals["latency_ms"] += agg["latency_ms"]
        totals["calls"] += agg["calls"]
        per_project.append({"project_id": pid, **agg})

    per_project.sort(key=lambda p: p["cost_cents"], reverse=True)
    return {"totals": totals, "per_project": per_project}