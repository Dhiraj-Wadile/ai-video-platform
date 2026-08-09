import time
from typing import List, Optional, AsyncIterator
import anthropic

from app.providers.base import LLMProvider, LLMResponse
from app.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.default_model = "claude-sonnet-4-20250514"

    async def complete(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        start = time.time()

        system_message = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        response = await self.client.messages.create(
            model=model or self.default_model,
            system=system_message,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = int((time.time() - start) * 1000)

        content = response.content[0].text if response.content else ""

        return LLMResponse(
            content=content,
            model=response.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=latency_ms,
            cost_cents=self._estimate_cost(response.model, response.usage),
        )

    async def stream(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        system_message = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        async with self.client.messages.stream(
            model=model or self.default_model,
            system=system_message,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def _estimate_cost(self, model: str, usage) -> int:
        pricing = {
            "claude-sonnet-4-20250514": {"input": 3, "output": 15},
            "claude-3-5-sonnet-20241022": {"input": 3, "output": 15},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        }
        rates = pricing.get(model, pricing["claude-sonnet-4-20250514"])
        cost = (usage.input_tokens * rates["input"] + usage.output_tokens * rates["output"]) / 1_000_000
        return int(cost * 100)
