import httpx
from typing import List, Optional

from app.providers.base import ImageProvider, ImageResult


class PollinationsProvider(ImageProvider):
    """Free image generation via Pollinations.ai"""

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

        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                return [ImageResult(url=url, revised_prompt=prompt)]

        return [ImageResult(url="", revised_prompt=prompt)]


class MockImageProvider(ImageProvider):
    """Mock image provider for development."""

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1792",
        quality: str = "standard",
        n: int = 1,
    ) -> List[ImageResult]:
        return [
            ImageResult(
                url=f"https://via.placeholder.com/{size.replace('x', 'x')}?text=AI+Generated",
                revised_prompt=prompt,
            )
            for _ in range(n)
        ]
