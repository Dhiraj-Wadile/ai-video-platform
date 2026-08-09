import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.types import UUIDType, JSONType


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    APPROVED = "approved"
    RENDERING = "rendering"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class ProjectType(str, enum.Enum):
    SHORT_FORM = "short_form"
    LONG_FORM = "long_form"
    COMEDY = "comedy"
    EDUCATIONAL = "educational"
    STORYTELLING = "storytelling"


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="draft")
    project_type = Column(String(20), default="short_form")
    platform = Column(String(50))
    settings_json = Column(JSONType, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="projects")
    script = relationship("Script", back_populates="project", uselist=False)
    scenes = relationship("Scene", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    generation_jobs = relationship("GenerationJob", back_populates="project")
    analytics = relationship("VideoAnalytics", back_populates="project")
