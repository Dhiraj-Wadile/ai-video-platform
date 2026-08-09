import json
from app.agents.base import BaseAgent, AgentInput, AgentOutput


class CharacterAgent(BaseAgent):
    name = "character_agent"
    description = "Creates original fictional characters for video content"
    model = "gpt-4o"

    SYSTEM_PROMPT = """You are a creative character designer for short-form video content.

Create original, memorable fictional characters. Do NOT clone or imitate real people, celebrities, or influencers.

Character configuration must include:
- Name (memorable, unique)
- Appearance (detailed visual description)
- Personality (key traits)
- Voice (tone, pitch, style)
- Speaking style (how they talk)
- Emotion (default emotional state)
- Catchphrases (2-3 memorable phrases)
- Background (brief backstory)
- Behavior (how they act)
- Relationships (with other characters)

Rules:
- Characters must be ORIGINAL
- Do NOT reference real people
- Make them memorable and distinctive
- Ensure they work across multiple videos
- Include visual consistency notes for AI image generation

Return ONLY valid JSON:
{
    "name": "Character Name",
    "appearance": "Detailed visual description for consistent rendering",
    "personality": "Key personality traits",
    "voice": "Voice description",
    "speaking_style": "How they talk",
    "emotion": "Default emotional state",
    "catchphrases": ["phrase 1", "phrase 2", "phrase 3"],
    "background": "Brief backstory",
    "behavior": "Behavioral patterns",
    "relationships": [],
    "visual_prompt": "Text-to-image prompt for generating this character"
}"""

    def build_messages(self, input: AgentInput) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a character for this context:\n\n{input.content}\n\nType: {input.context.get('type', 'general')}\nExisting characters: {json.dumps(input.context.get('existing_characters', []))}"},
        ]

    def parse_response(self, content: str) -> AgentOutput:
        try:
            cleaned = content.replace("```json\n", "").replace("```\n", "").strip()
            data = json.loads(cleaned)
            return AgentOutput(content=content, structured_data=data)
        except json.JSONDecodeError:
            return AgentOutput(content=content, structured_data={"name": "Unknown Character"})
