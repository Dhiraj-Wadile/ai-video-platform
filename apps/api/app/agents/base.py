from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid

from app.providers.base import LLMProvider


@dataclass
class AgentInput:
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    name: str = "base_agent"
    description: str = ""
    model: str = ""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def run(self, input: AgentInput) -> AgentOutput:
        start_time = time.time()

        await self.validate_input(input)

        messages = self.build_messages(input)
        response = await self.llm.complete(messages, model=self.model)

        output = self.parse_response(response.content)
        await self.validate_output(output)

        latency_ms = int((time.time() - start_time) * 1000)

        output.metadata.update({
            "agent": self.name,
            "model": response.model,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "latency_ms": latency_ms,
            "cost_cents": response.cost_cents,
        })

        return output

    @abstractmethod
    def build_messages(self, input: AgentInput) -> list:
        pass

    @abstractmethod
    def parse_response(self, content: str) -> AgentOutput:
        pass

    async def validate_input(self, input: AgentInput) -> bool:
        return True

    async def validate_output(self, output: AgentOutput) -> bool:
        return True
