from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.core.llm_output import parse_json_object


class ScriptAgent(BaseAgent):
    name = "script_agent"
    description = "Generates short-form video scripts optimized for retention"
    model = "gpt-4o"

    SYSTEM_PROMPT = """You are a viral short-form video scriptwriter.

Generate scripts optimized for maximum retention and engagement.

Structure:
HOOK (0-3s) - Shocking statement, curiosity gap
SETUP (3-8s) - Relatable context
CURIOSITY/CONFLICT (8-20s) - Build tension
PAYOFF (20-end) - Satisfying resolution
CTA (last 2-3s) - Call to action

Rules:
- Match the requested duration exactly
- Use short, punchy sentences
- Every word must earn its place
- End with a strong payoff
- Include a clear CTA

Return ONLY valid JSON with this structure:
{
    "title": "Script title",
    "duration": 30,
    "sections": {
        "hook": "The hook text",
        "setup": "The setup text",
        "conflict": "The conflict/curiosity text",
        "payoff": "The payoff text",
        "cta": "The call to action"
    },
    "full_script": "Complete script as one piece",
    "word_count": 80,
    "estimated_retention": "high"
}"""

    def build_messages(self, input: AgentInput) -> list:
        duration = input.context.get("duration", "30s")
        style = input.context.get("style", "educational")
        topic = input.content

        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Write a {duration} {style} script about: {topic}\n\nAdditional context: {input.context.get('additional_context', 'None')}"},
        ]

    def parse_response(self, content: str) -> AgentOutput:
        data = parse_json_object(content)
        # No JSON at all: treat the raw text as the script rather than losing it.
        if not data:
            return AgentOutput(content=content, structured_data={"full_script": content})
        return AgentOutput(content=content, structured_data=data)
