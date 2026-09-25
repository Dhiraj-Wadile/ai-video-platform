from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.registry import get_agent
from app.config import settings
from app.models.quality import QualityReview
from app.models.project import Project


def _gate_passed(review: QualityReview) -> bool:
    return (review.overall_score or 0) >= settings.qa_threshold and bool(review.safe_to_publish)


class QualityGate:
    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    async def review(
        self,
        project_id: str,
        script: str,
        scenes: list,
        db: AsyncSession,
        source: str = "manual",
    ) -> QualityReview:
        from app.providers.router import provider_router
        from app.providers.base import ProviderTask

        llm = self.llm or provider_router.resolve(ProviderTask.LLM)
        agent = get_agent("quality", llm)

        result = await agent.run({
            "content": script,
            "context": {"scenes": scenes or []},
        })

        data = result.structured_data or {}
        review = QualityReview(
            project_id=project_id,
            overall_score=int(data.get("overall_score", 0) or 0),
            breakdown_json=data.get("breakdown") or {},
            problems_json=data.get("problems") or [],
            recommendations_json=data.get("recommendations") or [],
            safe_to_publish=bool(data.get("safe_to_publish", False)),
            source=source,
        )
        db.add(review)
        await db.flush()

        project_row = await db.execute(select(Project).where(Project.id == project_id))
        project = project_row.scalar_one_or_none()
        if not _gate_passed(review) and project is not None:
            project.status = "review"

        return review

    @staticmethod
    async def latest(db: AsyncSession, project_id: str) -> Optional[QualityReview]:
        result = await db.execute(
            select(QualityReview)
            .where(QualityReview.project_id == project_id)
            .order_by(QualityReview.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()