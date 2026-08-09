from typing import List, Optional, AsyncIterator
from app.providers.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for development and testing."""

    async def complete(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        user_message = next((m["content"] for m in messages if m["role"] == "user"), "")

        mock_response = f"""{{
            "hook": "Did you know this mind-blowing fact?",
            "problem": "Most people don't understand this concept.",
            "explanation": "Here's the simple explanation that will change how you think.",
            "interestingFact": "The most surprising fact is that this affects everyone.",
            "conclusion": "Now you understand the secret behind this concept.",
            "callToAction": "Follow for more mind-blowing facts!",
            "fullScript": "Did you know this mind-blowing fact? Most people don't understand this concept. Here's the simple explanation that will change how you think. The most surprising fact is that this affects everyone. Now you understand the secret behind this concept. Follow for more mind-blowing facts!"
        }}"""

        return LLMResponse(
            content=mock_response,
            model="mock-model",
            tokens_in=len(user_message.split()),
            tokens_out=len(mock_response.split()),
            latency_ms=100,
            cost_cents=0,
        )

    async def stream(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        response = await self.complete(messages, model, temperature, max_tokens)
        words = response.content.split()
        for word in words:
            yield word + " "
