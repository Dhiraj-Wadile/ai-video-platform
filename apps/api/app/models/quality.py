import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey

from app.database import Base
from app.models.types import UUIDType, JSONType


class QualityReview(Base):
    __tablename__ = "quality_reviews"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)
    breakdown_json = Column(JSONType)
    problems_json = Column(JSONType)
    recommendations_json = Column(JSONType)
    safe_to_publish = Column(Boolean)
    source = Column(String(20))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))