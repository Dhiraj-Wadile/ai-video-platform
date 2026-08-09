from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.agents.registry import get_agent
from app.providers.llm.openai import OpenAIProvider

router = APIRouter()


class CharacterCreate(BaseModel):
    name: str
    description: Optional[str] = None
    character_type: str = "general"


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    voice_config: Optional[dict] = None
    speaking_style: Optional[str] = None
    catchphrases: Optional[List[str]] = None
    background: Optional[str] = None


class CharacterResponse(BaseModel):
    id: str
    name: str
    appearance: Optional[str]
    personality: Optional[str]
    speaking_style: Optional[str]
    catchphrases: Optional[list]
    background: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


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
    llm = OpenAIProvider()
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

    for field, value in request.dict(exclude_unset=True).items():
        setattr(character, field, value)

    await db.flush()
    return character
