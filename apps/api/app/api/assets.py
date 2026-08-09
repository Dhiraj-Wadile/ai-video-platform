from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List

from app.core.security import get_current_user

router = APIRouter()


class AssetUploadResponse(BaseModel):
    url: str
    key: str


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = "image",
    project_id: Optional[str] = None,
    user = Depends(get_current_user),
):
    from app.services.storage_service import get_storage, generate_asset_key

    storage = get_storage()
    ext = "png" if asset_type == "image" else "mp4" if asset_type == "video" else "mp3"
    key = generate_asset_key(project_id or "general", asset_type, ext)
    contents = await file.read()
    await storage.upload(contents, key, file.content_type or f"{asset_type}/{ext}")
    url = await storage.get_url(key)
    return AssetUploadResponse(url=url, key=key)


@router.get("/{asset_key}")
async def get_asset_url(
    asset_key: str,
    user = Depends(get_current_user),
):
    from app.services.storage_service import get_storage
    storage = get_storage()
    url = await storage.get_url(asset_key)
    return {"url": url}
