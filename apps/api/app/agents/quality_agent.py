import json
from app.agents.base import BaseAgent, AgentInput, AgentOutput


class QualityAgent(BaseAgent):
    name = "quality_agent"
    description = "Performs AI quality checks on generated content"
    model = "gpt-4o"

    SYSTEM_PROMPT = """You are a quality assurance expert for short-form video content.

Analyze the given content and provide a comprehensive quality assessment.

Check:
1. Hook quality (0-100)
2. Script quality (0-100)
3. Grammar and clarity (0-100)
4. Scene continuity (0-100)
5. Character consistency (0-100)
6. Estimated retention potential (0-100)
7. Platform formatting compliance
8. Any unsafe or inappropriate content
9. Copyright risk indicators

Return ONLY valid JSON:
{
    "overall_score": 87,
    "breakdown": {
        "hook_quality": 92,
        "script_quality": 85,
        "grammar": 95,
        "scene_continuity": 80,
        "character_consistency": 88,
        "retention_potential": 82
    },
    "problems": [
        {"severity": "high", "description": "problem description", "suggestion": "fix suggestion"}
    ],
    "recommendations": [
        "recommendation 1",
        "recommendation 2"
    ],
    "platform_compliance": {
        "youtube_shorts": true,
        "instagram_reels": true,
        "tiktok": true
    },
    "safe_to_publish": true
}"""

    def build_messages(self, input: AgentInput) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Perform quality check on this content:\n\n{input.content}\n\nContext: {json.dumps(input.context)}"},
        ]

    def parse_response(self, content: str) -> AgentOutput:
        try:
            cleaned = content.replace("```json\n", "").replace("```\n", "").strip()
            data = json.loads(cleaned)
            return AgentOutput(content=content, structured_data=data)
        except json.JSONDecodeError:
            return AgentOutput(content=content, structured_data={"overall_score": 0, "problems": []})
