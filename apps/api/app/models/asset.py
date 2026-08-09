import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUIDType, JSONType


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    type = Column(String(20), nullable=False)
    url = Column(String(500), nullable=False)
    metadata_json = Column(JSONType, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="assets")
