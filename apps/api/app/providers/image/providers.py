import httpx
from typing import List

from app.providers.base import (
    ImageProvider,
    ImageResult,
    ProviderInfoMixin,
    ProviderRequestError,
    ProviderTask,
)


class PollinationsProvider(ImageProvider, ProviderInfoMixin):
    """Free image generation via Pollinations.ai"""

    name = "pollinations"
    vendor = "pollinations.ai"
    capability = ProviderTask.IMAGE
    priority = 20
    models = ["flux"]

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1792",
        quality: str = "standard",
        n: int = 1,
    ) -> List[ImageResult]:
        width, height = size.split("x")
        encoded_prompt = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise ProviderRequestError(self.name, f"image request failed: {exc}") from exc

        if response.status_code != 200:
            raise ProviderRequestError(
                self.name, f"image request returned HTTP {response.status_code}"
            )

        return [ImageResult(url=url, revised_prompt=prompt)]
