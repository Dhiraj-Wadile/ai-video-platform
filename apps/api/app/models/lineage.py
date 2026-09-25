import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey

from app.database import Base
from app.models.types import UUIDType, JSONType


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    task = Column(String(30), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100))
    status = Column(String(20), nullable=False)
    cost_cents = Column(Integer)
    latency_ms = Column(Integer)
    parent_id = Column(String(36))
    context_json = Column(JSONType)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))