from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.registry import get_agent
from app.config import settings
from app.core.llm_output import as_dict, coerce_int
from app.models.quality import QualityReview
from app.models.project import Project


def _gate_passed(review: QualityReview) -> bool:
    return (review.overall_score or 0) >= settings.qa_threshold and bool(review.safe_to_publish)


class QualityGate:
    def __init__(self, llm_provider_name: Optional[str] = None):
        # A provider *name*, resolved through the router. Accepting a provider instance
        # here meant a client could post an arbitrary JSON value and have it installed
        # as the LLM, which failed at the first .complete() call.
        self.llm_provider_name = llm_provider_name

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

        llm = provider_router.resolve(ProviderTask.LLM, name=self.llm_provider_name)
        agent = get_agent("quality", llm)

        result = await agent.run({
            "content": script,
            "context": {"scenes": scenes or []},
        })

        # The quality agent asks for an object but a list/scalar is a valid model
        # response; as_dict guarantees the .get calls below cannot raise.
        data = as_dict(result.structured_data)
        review = QualityReview(
            project_id=project_id,
            overall_score=coerce_int(data.get("overall_score"), 0) or 0,
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