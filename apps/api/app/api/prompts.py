from fastapi import APIRouter, Depends
from pydantic import BaseModel
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
    version: int
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class PromptUpdate(BaseModel):
    content: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptTemplate).order_by(PromptTemplate.category))
    return result.scalars().all()


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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prompt not found")

    if request.content is not None:
        prompt.content = request.content
        prompt.version += 1
    if request.is_active is not None:
        prompt.is_active = request.is_active

    await db.flush()
    return prompt
