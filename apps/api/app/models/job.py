import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUIDType, JSONType


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), default="queued")
    input_json = Column(JSONType)
    output_json = Column(JSONType)
    model = Column(String(100))
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    latency_ms = Column(Integer)
    cost_cents = Column(Integer)
    error = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)

    project = relationship("Project", back_populates="generation_jobs")


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    status = Column(String(20), default="queued")
    progress = Column(Integer, default=0)
    output_url = Column(String(500))
    format = Column(String(20), default="mp4")
    resolution = Column(String(20), default="1080x1920")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)


class PublishingJob(Base):
    __tablename__ = "publishing_jobs"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    platform = Column(String(50), nullable=False)
    status = Column(String(20), default="queued")
    external_id = Column(String(255))
    published_url = Column(String(500))
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    error = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
