import os
from typing import Optional

from app.providers.base import VideoProvider, VideoResult, ProviderInfoMixin, ProviderTask
from app.config import settings


class HiggsfieldVideoProvider(VideoProvider, ProviderInfoMixin):
    """Higgsfield video generation via the official `higgsfield-client` SDK.

    Calls ``subscribe_async(model, arguments={...})`` which submits, polls, and waits
    for the terminal result. Models are account-catalog-specific; the slug comes from
    ``settings.higgsfield_video_model``.
    """

    name = "higgsfield"
    vendor = "higgsfield.ai"
    capability = ProviderTask.VIDEO
    priority = 5
    models = ["higgsfield_video_model"]

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.higgsfield_api_key)

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        image_url: Optional[str] = None,
    ) -> VideoResult:
        if not settings.higgsfield_video_model:
            raise RuntimeError(
                "HIGGSFIELD_VIDEO_MODEL is not configured; set it to a model slug "
                "available to your account (e.g. via https://console.higgsfield.ai)."
            )

        try:
            import higgsfield_client
        except ImportError:
            raise RuntimeError(
                "higgsfield-client is not installed; run: pip install higgsfield-client"
            )

        os.environ["HF_KEY"] = settings.higgsfield_api_key

        arguments = {"prompt": prompt}
        if image_url:
            arguments["image_url"] = image_url

        result = await higgsfield_client.subscribe_async(
            settings.higgsfield_video_model,
            arguments=arguments,
        )

        status = result.get("status")
        if status in ("failed", "nsfw", "canceled"):
            raise RuntimeError(f"Higgsfield generation {status}: {result.get('error') or 'no detail'}")

        video = result.get("video") or {}
        url = video.get("url") or (result.get("videos") or [{}])[0].get("url")
        if not url:
            raise RuntimeError(f"Higgsfield completed without a video URL: {result}")

        return VideoResult(url=url, duration_seconds=duration)