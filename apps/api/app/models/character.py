import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUIDType, JSONType


class Character(Base):
    __tablename__ = "characters"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    appearance = Column(Text)
    personality = Column(Text)
    voice_config_json = Column(JSONType)
    speaking_style = Column(Text)
    catchphrases = Column(JSONType)
    background = Column(Text)
    behavior = Column(Text)
    relationships = Column(JSONType)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="characters")
