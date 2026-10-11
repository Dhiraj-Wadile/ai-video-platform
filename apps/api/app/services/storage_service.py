import asyncio
import hashlib
import hmac
import io
import os
import re
import time
import uuid
import httpx
from typing import Optional
from abc import ABC, abstractmethod
from urllib.parse import quote, urlencode

from app.config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        pass

    @abstractmethod
    async def get_url(self, key: str) -> str:
        pass

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """Fetch the bytes behind a key. Used by the signed /media route."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass


ALLOWED_ASSET_TYPES = {"image": "png", "video": "mp4", "audio": "mp3"}

# Internal kinds also used by the pipeline (e.g. "scene_image"); any lowercase slug is a valid path
# segment, but nothing containing separators or dots is.
KEY_SEGMENT_RE = re.compile(r"^[a-z0-9_]{1,32}$")
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

MEDIA_URL_TTL_SECONDS = 60 * 60 * 24  # 24h
LOCAL_URL_PREFIX = "/storage/"


def media_signature(key: str, expires_at: int) -> str:
    """HMAC over the key and expiry, keyed by JWT_SECRET."""
    payload = f"{key}:{expires_at}".encode()
    return hmac.new(
        settings.jwt_secret.encode(), payload, hashlib.sha256
    ).hexdigest()


def verify_media_signature(key: str, expires_at: Optional[str], signature: Optional[str]) -> bool:
    """Constant-time check of a signed media URL. Rejects missing/expired/bad signatures."""
    if not expires_at or not signature:
        return False
    try:
        expiry = int(expires_at)
    except (TypeError, ValueError):
        return False
    if expiry < int(time.time()):
        return False
    return hmac.compare_digest(media_signature(key, expiry), signature)


def sign_media_url(url: str, ttl_seconds: int = MEDIA_URL_TTL_SECONDS) -> str:
    """Add a signature to a local media URL so it can be loaded by an <img>/<video>.

    Bytes must never be served straight from a public mount - every rendered frame and
    narration would be readable by anyone who learns the key, across tenants. URLs are
    only signed after an ownership check has passed, so this preserves the `<img src>`
    flow the UI depends on without exposing other users' media.
    """
    if not url or not url.startswith(LOCAL_URL_PREFIX):
        # S3/MinIO and already-signed URLs are passed through untouched.
        return url
    key = url[len(LOCAL_URL_PREFIX):].split("?", 1)[0]
    if not key:
        return url
    expires_at = int(time.time()) + ttl_seconds
    query = urlencode({"exp": expires_at, "sig": media_signature(key, expires_at)})
    return f"{LOCAL_URL_PREFIX}{quote(key)}?{query}"


def storage_key_from_url(url: str) -> Optional[str]:
    """Inverse of LocalStorage.get_url - recovers the key from a stored URL."""
    if not url or not url.startswith(LOCAL_URL_PREFIX):
        return None
    return url[len(LOCAL_URL_PREFIX):].split("?", 1)[0] or None


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str = None):
        self.base_dir = os.path.abspath(base_dir or settings.storage_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve(self, key: str) -> str:
        """Resolve a key inside the storage root, refusing traversal or absolute paths."""
        if not key or key.startswith("/") or key.startswith("\\") or ".." in key.split("/"):
            raise ValueError("Invalid storage key")
        path = os.path.abspath(os.path.join(self.base_dir, key))
        if not path.startswith(self.base_dir + os.sep):
            raise ValueError("Invalid storage key")
        return path

    def _write(self, path: str, data: bytes) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        # Disk I/O is synchronous; on the event loop it stalls every concurrent request
        # for the duration of a large write.
        await asyncio.to_thread(self._write, path, data)
        return key

    async def get_url(self, key: str) -> str:
        return f"{LOCAL_URL_PREFIX}{key}"

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        return await asyncio.to_thread(lambda: open(path, "rb").read())

    def _delete(self, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def delete(self, key: str) -> bool:
        path = self._resolve(key)
        return await asyncio.to_thread(self._delete, path)


class S3Storage(StorageBackend):
    def __init__(self):
        import boto3
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        self.bucket = settings.s3_bucket

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get_url(self, key: str) -> str:
        return f"{settings.s3_endpoint}/{self.bucket}/{key}"

    async def read(self, key: str) -> bytes:
        def _get() -> bytes:
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket, key, buffer)
            return buffer.getvalue()

        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage() -> StorageBackend:
    use_s3 = settings.storage_backend.lower() == "s3" or (
        settings.storage_backend.lower() != "local" and settings.s3_endpoint and "localhost" not in settings.s3_endpoint
    )
    return S3Storage() if use_s3 else LocalStorage()


def generate_asset_key(project_id: str, asset_type: str, ext: str) -> str:
    """Build a storage key for a project asset.

    `asset_type` becomes a path segment, so it is restricted to a lowercase slug; `..`, separators and
    absolute paths are rejected before they can reach the filesystem or an object key.
    """
    if not KEY_SEGMENT_RE.match(asset_type or ""):
        raise ValueError(f"Invalid asset type: {asset_type!r}")
    if not project_id or not PROJECT_ID_RE.match(str(project_id)):
        raise ValueError(f"Invalid project id: {project_id!r}")
    if not KEY_SEGMENT_RE.match(ext or ""):
        raise ValueError(f"Invalid extension: {ext!r}")
    return f"projects/{project_id}/{asset_type}/{uuid.uuid4().hex[:12]}.{ext}"
