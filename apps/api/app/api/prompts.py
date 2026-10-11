from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.prompt import PromptTemplate

router = APIRouter()


class PromptResponse(BaseModel):
    id: str
    name: str
    category: str
    content: str
    version: int = 0
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("version", "is_active", mode="before")
    @classmethod
    def nullable_columns(cls, v, info):
        # The columns are nullable, so pre-existing rows may hold NULL; never 500 on them.
        return False if v is None and info.field_name == "is_active" else (0 if v is None else v)

    @field_serializer("created_at")
    def serialize_created_at(self, v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if isinstance(v, datetime) else v



class PromptUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=50_000)
    is_active: Optional[bool] = None


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1, max_length=50_000)
    is_active: Optional[bool] = True


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptTemplate).order_by(PromptTemplate.category))
    return result.scalars().all()


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    request: PromptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prompt = PromptTemplate(
        name=request.name,
        category=request.category,
        content=request.content,
        is_active=True if request.is_active is None else request.is_active,
        user_id=user.id,
    )
    db.add(prompt)
    await db.flush()
    return prompt


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    request: PromptUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Templates have no owner column historically, so any authenticated user could rewrite
    # every other account's prompts. Global rows (user_id NULL) are read-only.
    if prompt.user_id is None:
        raise HTTPException(status_code=403, detail="Global prompt templates are read-only")
    if str(prompt.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Prompt not found")

    if request.content is not None:
        prompt.content = request.content
        prompt.version = (prompt.version or 0) + 1
    if request.is_active is not None:
        prompt.is_active = request.is_active

    await db.flush()
    return prompt


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if prompt.user_id is None:
        raise HTTPException(status_code=403, detail="Global prompt templates cannot be deleted")
    if str(prompt.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Prompt not found")

    await db.delete(prompt)
    await db.flush()
    return Response(status_code=204)
