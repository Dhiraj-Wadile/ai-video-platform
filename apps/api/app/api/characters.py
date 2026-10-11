from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.agents.registry import get_agent
from app.providers.base import ProviderTask
from app.providers.router import get_provider

router = APIRouter()


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=10_000)
    character_type: str = Field("general", max_length=50)


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    appearance: Optional[str] = Field(None, max_length=10_000)
    personality: Optional[str] = Field(None, max_length=10_000)
    voice_config: Optional[dict] = None
    speaking_style: Optional[str] = Field(None, max_length=2_000)
    catchphrases: Optional[List[str]] = None
    background: Optional[str] = Field(None, max_length=10_000)


class CharacterResponse(BaseModel):
    id: str
    name: str
    appearance: Optional[str]
    personality: Optional[str]
    speaking_style: Optional[str]
    catchphrases: Optional[list]
    background: Optional[str]
    voice_config: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def read_voice_config_column(cls, data):
        """`voice_config_json` is the column; expose it as `voice_config`."""
        if hasattr(data, "voice_config_json"):
            return {
                "id": data.id,
                "name": data.name,
                "appearance": data.appearance,
                "personality": data.personality,
                "speaking_style": data.speaking_style,
                "catchphrases": data.catchphrases,
                "background": data.background,
                "voice_config": data.voice_config_json,
                "created_at": data.created_at,
            }
        return data

    @field_serializer("created_at")
    def serialize_created_at(self, v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if isinstance(v, datetime) else v


@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character).where(Character.user_id == user.id).order_by(Character.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=CharacterResponse)
async def create_character(
    request: CharacterCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    llm = get_provider(ProviderTask.LLM)
    agent = get_agent("character", llm)

    result = await agent.run({
        "content": request.description or f"Create a {request.character_type} character named {request.name}",
        "context": {
            "type": request.character_type,
            "existing_characters": [],
        }
    })

    data = result.structured_data or {}
    character = Character(
        user_id=user.id,
        name=data.get("name", request.name),
        appearance=data.get("appearance"),
        personality=data.get("personality"),
        speaking_style=data.get("speaking_style"),
        catchphrases=data.get("catchphrases", []),
        background=data.get("background"),
    )
    db.add(character)
    await db.flush()
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    request: CharacterUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    data = request.model_dump(exclude_unset=True)
    if "voice_config" in data:
        data["voice_config_json"] = data.pop("voice_config")
    for field, value in data.items():
        if not hasattr(Character, field):
            raise HTTPException(status_code=422, detail=f"Unknown field '{field}'")
        if value is None and getattr(Character, field).nullable is False:
            raise HTTPException(status_code=422, detail=f"Field '{field}' cannot be null")
        setattr(character, field, value)

    await db.flush()
    return character
