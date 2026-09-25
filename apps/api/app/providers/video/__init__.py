import httpx
import time
import hashlib
import json
from typing import Optional

from app.providers.base import VideoProvider, VideoResult, ProviderInfoMixin, ProviderTask
from app.config import settings


class PollinationsVideoProvider(VideoProvider, ProviderInfoMixin):
    """Free video generation via Pollinations.ai (image-to-video)."""

    name = "pollinations"
    vendor = "pollinations.ai"
    capability = ProviderTask.VIDEO
    priority = 20

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        image_url: Optional[str] = None,
    ) -> VideoResult:
        encoded_prompt = prompt.replace(" ", "%20")
        seed = int(time.time()) % 10000

        if image_url:
            url = f"https://video.pollinations.ai/{encoded_prompt}?image={image_url}&seed={seed}"
        else:
            url = f"https://video.pollinations.ai/{encoded_prompt}?seed={seed}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                return VideoResult(
                    url=url,
                    duration_seconds=duration,
                )

        return VideoResult(url="", duration_seconds=duration)


class RunwayVideoProvider(VideoProvider, ProviderInfoMixin):
    """Runway ML video generation provider."""

    name = "runway"
    vendor = "runwayml"
    capability = ProviderTask.VIDEO
    priority = 10
    models = ["gen3a_turbo"]

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.runway_api_key)

    def __init__(self):
        self.api_key = settings.runway_api_key
        self.base_url = "https://api.runwayml.com/v1"

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        image_url: Optional[str] = None,
    ) -> VideoResult:
        if not self.api_key:
            raise ValueError("Runway API key not configured")

        async with httpx.AsyncClient(timeout=120.0) as client:
            body = {
                "promptText": prompt,
                "duration": int(duration),
                "model": "gen3a_turbo",
            }
            if image_url:
                body["image"] = image_url

            response = await client.post(
                f"{self.base_url}/image_to_video",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("id", "")

            import asyncio
            for _ in range(60):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                status_data = status_resp.json()
                if status_data.get("status") == "SUCCEEDED":
                    video_url = status_data.get("output", [None])[0]
                    return VideoResult(url=video_url or "", duration_seconds=duration)
                elif status_data.get("status") == "FAILED":
                    raise RuntimeError(f"Runway generation failed: {status_data.get('error')}")

        return VideoResult(url="", duration_seconds=duration)
