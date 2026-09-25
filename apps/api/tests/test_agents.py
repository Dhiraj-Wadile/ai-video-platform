import json

import pytest

from app.agents.base import AgentInput
from app.agents.script_agent import ScriptAgent
from app.agents.trend_agent import TrendAgent
from app.providers.base import LLMProvider, LLMResponse


class FakeLLM(LLMProvider):
    def __init__(self, content: str):
        self._content = content

    async def complete(
        self,
        messages,
        model=None,
        temperature=0.7,
        max_tokens=4096,
        response_format=None,
    ) -> LLMResponse:
        return LLMResponse(
            content=self._content,
            model=model or "gpt-4o",
            tokens_in=10,
            tokens_out=12,
            latency_ms=5,
            cost_cents=0,
        )

    async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
        yield self._content


SCRIPT_JSON = json.dumps({
    "title": "Winter Hiking",
    "duration": 30,
    "sections": {"hook": "H", "setup": "S", "conflict": "C", "payoff": "P", "cta": "CTA"},
    "full_script": "Winter hiking is amazing.",
    "word_count": 5,
    "estimated_retention": "high",
})


@pytest.mark.anyio
async def test_script_agent_accepts_dict_input():
    llm = FakeLLM(SCRIPT_JSON)
    agent = ScriptAgent(llm)

    result = await agent.run({
        "content": "winter hiking",
        "context": {"duration": "30s", "style": "educational"},
    })

    assert result.structured_data["title"] == "Winter Hiking"
    assert result.structured_data["duration"] == 30
    assert result.metadata["agent"] == "script_agent"
    assert result.metadata["model"] == "gpt-4o"


@pytest.mark.anyio
async def test_agent_run_defaults_missing_context():
    llm = FakeLLM('{"topic": "memes", "trend_score": 50}')
    agent = TrendAgent(llm)

    result = await agent.run({"content": "memes"})

    assert result.structured_data["trend_score"] == 50
    assert result.content


@pytest.mark.anyio
async def test_agent_run_accepts_dataclass_input():
    llm = FakeLLM(SCRIPT_JSON)
    agent = ScriptAgent(llm)

    result = await agent.run(AgentInput(content="winter hiking", context={"duration": "30s"}))

    assert result.structured_data["title"] == "Winter Hiking"


@pytest.mark.anyio
async def test_agent_run_handles_non_json_response():
    llm = FakeLLM("No structured data here, just prose")
    agent = ScriptAgent(llm)

    result = await agent.run({"content": "topic"})

    assert result.structured_data is None or result.content