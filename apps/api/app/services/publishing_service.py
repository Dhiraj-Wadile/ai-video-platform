"""Publishing to social platforms.

Each platform is behind a small adapter. When the platform's credentials are not
configured, the account silently falls back to :class:`MockPublisher` so scheduling can be
demonstrated without live keys; the resulting job records ``provider="mock"`` so the caller
can tell a real publish from a simulated one.

Real publishers need the rendered video to be reachable:
- Instagram is URL-based, so it needs a publicly reachable ``media_url``.
- YouTube and TikTok upload bytes, so they need ``video_bytes``.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


SUPPORTED_PLATFORMS = ("youtube", "tiktok", "instagram")


@dataclass
class PublishContext:
    project_id: str
    title: str
    caption: str
    media_url: Optional[str] = None
    video_bytes: Optional[bytes] = None


@dataclass
class PublishResult:
    external_id: str
    published_url: str
    provider: str


class PublisherError(Exception):
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider}: {message}")


class Publisher:
    name = ""
    label = ""
    is_mock = False
    priority = 100

    @classmethod
    def is_configured(cls) -> bool:
        raise NotImplementedError

    async def publish(self, ctx: PublishContext) -> PublishResult:
        raise NotImplementedError


class MockPublisher(Publisher):
    """Simulates a successful publish. Always available, lowest priority."""

    name = "mock"
    label = "Simulated"
    is_mock = True
    priority = 1000

    @classmethod
    def is_configured(cls) -> bool:
        return True

    async def publish(self, ctx: PublishContext) -> PublishResult:
        token = uuid.uuid4().hex[:12]
        return PublishResult(
            external_id=f"mock_{token}",
            published_url=f"https://example.com/simulated/{ctx.project_id[:8]}/{token}",
            provider="mock",
        )


class YouTubePublisher(Publisher):
    name = "youtube"
    label = "YouTube Shorts"
    priority = 10

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.youtube_access_token)

    async def publish(self, ctx: PublishContext) -> PublishResult:
        if not ctx.video_bytes:
            raise PublisherError(self.name, "a rendered video is required to upload")

        headers = {
            "Authorization": f"Bearer {settings.youtube_access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(len(ctx.video_bytes)),
        }
        metadata = {
            "snippet": {"title": ctx.title[:100], "description": ctx.caption[:5000]},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                init = await client.post(
                    "https://www.googleapis.com/upload/youtube/v3/videos",
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    headers=headers,
                    json=metadata,
                )
                if init.status_code not in (200, 201):
                    raise PublisherError(self.name, f"init failed HTTP {init.status_code}: {init.text[:200]}")
                upload_url = init.headers.get("Location")
                if not upload_url:
                    raise PublisherError(self.name, "no upload URL returned")

                upload = await client.put(
                    upload_url,
                    headers={"Content-Type": "video/mp4"},
                    content=ctx.video_bytes,
                )
                if upload.status_code not in (200, 201):
                    raise PublisherError(self.name, f"upload failed HTTP {upload.status_code}: {upload.text[:200]}")
                video_id = upload.json().get("id")
        except httpx.HTTPError as exc:
            raise PublisherError(self.name, f"network error: {exc}") from exc

        return PublishResult(
            external_id=video_id,
            published_url=f"https://youtube.com/shorts/{video_id}",
            provider=self.name,
        )


class TikTokPublisher(Publisher):
    name = "tiktok"
    label = "TikTok"
    priority = 20

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.tiktok_access_token)

    async def publish(self, ctx: PublishContext) -> PublishResult:
        if not ctx.video_bytes:
            raise PublisherError(self.name, "a rendered video is required to upload")

        size = len(ctx.video_bytes)
        headers = {
            "Authorization": f"Bearer {settings.tiktok_access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "post_info": {"title": ctx.title[:2200], "privacy_level": "PUBLIC_TO_EVERYONE"},
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                init = await client.post(
                    "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    headers=headers,
                    json=body,
                )
                if init.status_code not in (200, 201):
                    raise PublisherError(self.name, f"init failed HTTP {init.status_code}: {init.text[:200]}")
                data = init.json().get("data", {})
                upload_url = data.get("upload_url")
                publish_id = data.get("publish_id")
                if not upload_url:
                    raise PublisherError(self.name, "no upload URL returned")

                upload = await client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{size - 1}/{size}",
                    },
                    content=ctx.video_bytes,
                )
                if upload.status_code not in (200, 201):
                    raise PublisherError(self.name, f"upload failed HTTP {upload.status_code}")
        except httpx.HTTPError as exc:
            raise PublisherError(self.name, f"network error: {exc}") from exc

        return PublishResult(
            external_id=publish_id,
            published_url=f"https://www.tiktok.com/",
            provider=self.name,
        )


class InstagramPublisher(Publisher):
    name = "instagram"
    label = "Instagram Reels"
    priority = 20

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.meta_access_token and settings.instagram_business_account_id)

    async def publish(self, ctx: PublishContext) -> PublishResult:
        if not ctx.media_url:
            raise PublisherError(self.name, "a publicly reachable media URL is required")

        base = f"https://graph.facebook.com/v21.0/{settings.instagram_business_account_id}"
        token = settings.meta_access_token
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                create = await client.post(
                    f"{base}/media",
                    data={
                        "media_type": "REELS",
                        "video_url": ctx.media_url,
                        "caption": ctx.caption[:2200],
                        "access_token": token,
                    },
                )
                if create.status_code not in (200, 201):
                    raise PublisherError(self.name, f"container failed HTTP {create.status_code}: {create.text[:200]}")
                creation_id = create.json().get("id")

                publish = await client.post(
                    f"{base}/media_publish",
                    data={"creation_id": creation_id, "access_token": token},
                )
                if publish.status_code not in (200, 201):
                    raise PublisherError(self.name, f"publish failed HTTP {publish.status_code}: {publish.text[:200]}")
                media_id = publish.json().get("id")
        except httpx.HTTPError as exc:
            raise PublisherError(self.name, f"network error: {exc}") from exc

        return PublishResult(
            external_id=media_id,
            published_url=f"https://www.instagram.com/",
            provider=self.name,
        )


PUBLISHER_REGISTRY: Dict[str, type] = {
    "youtube": YouTubePublisher,
    "tiktok": TikTokPublisher,
    "instagram": InstagramPublisher,
}


def resolve_publisher(platform: str) -> Publisher:
    """Return the configured publisher for a platform, or the mock fallback."""
    cls = PUBLISHER_REGISTRY.get(platform)
    if cls is None:
        raise ValueError(f"Unsupported platform: {platform}")
    if cls.is_configured():
        return cls()
    return MockPublisher()


def platform_status() -> List[dict]:
    """Inventory of platforms and whether each has live credentials."""
    out = []
    for name in SUPPORTED_PLATFORMS:
        cls = PUBLISHER_REGISTRY[name]
        out.append({
            "platform": name,
            "label": cls.label,
            "configured": cls.is_configured(),
            "mode": "live" if cls.is_configured() else "simulated",
        })
    return out


# --- DB orchestration --------------------------------------------------------

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.models.job import PublishingJob  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.services.storage_service import (  # noqa: E402
    get_storage,
    sign_media_url,
    storage_key_from_url,
)


async def resolve_media(db: AsyncSession, project_id: str) -> tuple[Optional[str], Optional[bytes]]:
    """Return (public_media_url, video_bytes) for the project's latest rendered video."""
    result = await db.execute(
        select(Asset)
        .where(Asset.project_id == project_id, Asset.type == "video")
        .order_by(Asset.created_at.desc())
    )
    asset = result.scalars().first()
    if not asset or not asset.url:
        return None, None

    key = (asset.metadata_json or {}).get("key") or storage_key_from_url(asset.url)
    media_url = sign_media_url(asset.url)
    video_bytes = None
    if key:
        try:
            video_bytes = await get_storage().read(key)
        except Exception as exc:  # noqa: BLE001 - best effort; mock publishing needs no bytes
            logger.warning("Could not read rendered video %s: %s", key, exc)
    return media_url, video_bytes


async def publish_job(db: AsyncSession, job: PublishingJob) -> PublishingJob:
    """Perform (or simulate) the publish for one job and persist the outcome."""
    publisher = resolve_publisher(job.platform)
    media_url, video_bytes = await resolve_media(db, str(job.project_id))
    ctx = PublishContext(
        project_id=str(job.project_id),
        title=job.title or "",
        caption=job.caption or job.title or "",
        media_url=media_url,
        video_bytes=video_bytes,
    )

    job.status = "publishing"
    try:
        result = await publisher.publish(ctx)
    except PublisherError as exc:
        job.status = "failed"
        job.error = str(exc)
        job.provider = publisher.name
    else:
        job.status = "published"
        job.provider = result.provider
        job.external_id = result.external_id
        job.published_url = result.published_url
        job.published_at = datetime.now(timezone.utc)
        job.error = None

    await db.flush()
    return job


async def publish_due_jobs(limit: int = 20) -> int:
    """Publish every scheduled job whose time has arrived. Returns how many ran."""
    from app.database import async_session

    now = datetime.now(timezone.utc)
    published = 0
    async with async_session() as db:
        result = await db.execute(
            select(PublishingJob)
            .where(PublishingJob.status == "scheduled", PublishingJob.scheduled_at <= now)
            .order_by(PublishingJob.scheduled_at)
            .limit(limit)
        )
        jobs = result.scalars().all()
        for job in jobs:
            await publish_job(db, job)
            published += 1
        await db.commit()
    return published

