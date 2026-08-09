import os
import uuid
import httpx
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        pass

    @abstractmethod
    async def get_url(self, key: str) -> str:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        path = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    async def get_url(self, key: str) -> str:
        return f"/storage/{key}"

    async def delete(self, key: str) -> bool:
        path = os.path.join(self.base_dir, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


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

    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage() -> StorageBackend:
    if settings.s3_endpoint and "localhost" not in settings.s3_endpoint:
        return S3Storage()
    return LocalStorage()


def generate_asset_key(project_id: str, asset_type: str, ext: str) -> str:
    return f"projects/{project_id}/{asset_type}/{uuid.uuid4().hex[:12]}.{ext}"
