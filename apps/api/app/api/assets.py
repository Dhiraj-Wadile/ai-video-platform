from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.asset import Asset
from app.api.deps import owned_project_or_404, project_id_from_asset_key
from app.services.storage_service import (
    ALLOWED_ASSET_TYPES,
    generate_asset_key,
    get_storage,
    sign_media_url,
)

router = APIRouter()

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
ALLOWED_CONTENT_TYPES = {
    "image": {"image/png", "image/jpeg", "image/webp"},
    "video": {"video/mp4", "video/webm", "video/quicktime"},
    "audio": {"audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a"},
}


class AssetUploadResponse(BaseModel):
    url: str
    key: str


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    # Accept asset_type/project_id from either the multipart form (web client) or the
    # query string (API clients / integrations) so neither caller is rejected.
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    project_id = form.get("project_id") or request.query_params.get("project_id")
    asset_type = form.get("asset_type") or request.query_params.get("asset_type") or "image"

    if asset_type not in ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=422, detail=f"asset_type must be one of {sorted(ALLOWED_ASSET_TYPES)}")
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")

    await owned_project_or_404(db, project_id, user)

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES[asset_type]:
        raise HTTPException(status_code=422, detail=f"Unsupported content type for {asset_type}: {content_type or 'unknown'}")

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 100 MB limit")

    storage = get_storage()
    ext = ALLOWED_ASSET_TYPES[asset_type]
    key = generate_asset_key(project_id, asset_type, ext)
    await storage.upload(contents, key, content_type)
    # The row stores the stable key, never the expiring signed URL.
    stored_url = await storage.get_url(key)

    asset = Asset(
        project_id=project_id,
        type=asset_type,
        url=stored_url,
        metadata_json={"key": key, "mime_type": content_type, "file_size": len(contents)},
    )
    db.add(asset)
    await db.flush()

    return AssetUploadResponse(url=sign_media_url(stored_url), key=key)


@router.get("/{asset_key:path}")
async def get_asset_url(
    asset_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project_id = project_id_from_asset_key(asset_key)
    if project_id is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    await owned_project_or_404(db, project_id, user)

    storage = get_storage()
    url = sign_media_url(await storage.get_url(asset_key))
    return {"url": url}
