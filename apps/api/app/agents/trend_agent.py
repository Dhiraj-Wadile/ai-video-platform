import json
from app.agents.base import BaseAgent, AgentInput, AgentOutput


class TrendAgent(BaseAgent):
    name = "trend_agent"
    description = "Analyzes trending topics and identifies content opportunities"
    model = "gpt-4o"

    SYSTEM_PROMPT = """You are a trend analysis expert for short-form video content.

Analyze the given topic/data and identify:
1. Why it is trending
2. Why it may work as video content
3. Recommended hook
4. Recommended format (comedy, educational, storytelling, etc.)
5. Recommended duration (15s, 30s, 45s, 60s, 90s)
6. Suggested audience
7. Competition level (low, medium, high)
8. Trend score (1-100)

Return ONLY valid JSON with this structure:
{
    "topic": "the topic",
    "why_trending": "explanation",
    "why_it_works": "explanation",
    "recommended_hook": "a compelling hook line",
    "recommended_format": "format",
    "recommended_duration": "30s",
    "suggested_audience": "target audience",
    "competition": "medium",
    "trend_score": 75,
    "content_opportunities": ["opportunity 1", "opportunity 2"]
}"""

    def build_messages(self, input: AgentInput) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this trend/topic for video content potential:\n\n{input.content}"},
        ]

    def parse_response(self, content: str) -> AgentOutput:
        try:
            cleaned = content.replace("```json\n", "").replace("```\n", "").strip()
            data = json.loads(cleaned)
            return AgentOutput(content=content, structured_data=data)
        except json.JSONDecodeError:
            return AgentOutput(content=content, structured_data={"topic": content[:100]})
