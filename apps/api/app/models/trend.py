import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUIDType, JSONType


class Trend(Base):
    __tablename__ = "trends"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String(255), nullable=False)
    source = Column(String(100))
    score = Column(Float)
    metadata_json = Column(JSONType, default=dict)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class VideoAnalytics(Base):
    __tablename__ = "video_analytics"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    platform = Column(String(50))
    views = Column(Integer, default=0)
    watch_time_seconds = Column(Integer, default=0)
    retention_json = Column(JSONType)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    engagement_rate = Column(Float)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="analytics")


class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    analysis_json = Column(JSONType)
    recommendations_json = Column(JSONType)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
