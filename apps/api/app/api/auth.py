from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User
from app.core.security import create_access_token, pwd_context

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        name=request.name,
        password_hash=pwd_context.hash(request.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Two concurrent registrations for the same email both clear the SELECT above; the
        # unique constraint is what actually decides. Without this the loser saw a 500.
        await db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )
