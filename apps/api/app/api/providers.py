from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.providers.router import provider_router

router = APIRouter()


@router.get("")
async def list_providers(current_user=Depends(get_current_user)):
    return {"providers": provider_router.as_dicts()}