import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUIDType, JSONType


class Script(Base):
    __tablename__ = "scripts"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255))
    content = Column(Text, nullable=False)
    duration = Column(Integer)
    structure_json = Column(JSONType)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="script")
    scenes = relationship("Scene", back_populates="script")


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(UUIDType, ForeignKey("projects.id"), nullable=False)
    script_id = Column(UUIDType, ForeignKey("scripts.id"))
    scene_number = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    narration = Column(Text)
    visual_description = Column(Text)
    camera = Column(String(50))
    emotion = Column(String(50))
    background = Column(String(100))
    music_mood = Column(String(50))
    sfx = Column(String(50))
    caption = Column(Text)
    transition = Column(String(50))
    character_id = Column(UUIDType, ForeignKey("characters.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="scenes")
    script = relationship("Script", back_populates="scenes")
    character = relationship("Character")
