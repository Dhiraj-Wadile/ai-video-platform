import json
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.core.llm_output import parse_json


class StoryboardAgent(BaseAgent):
    name = "storyboard_agent"
    description = "Converts scripts into detailed scene-by-scene storyboards"
    model = "gpt-4o"

    SYSTEM_PROMPT = """You are a professional video storyboard artist and director.

Convert the given script into a detailed scene-by-scene storyboard.

Each scene must include:
- Scene number
- Duration (seconds)
- Character(s) present
- Dialogue (if any)
- Narration
- Visual description (cinematic, detailed)
- Camera movement
- Emotion/mood
- Background/setting
- Music mood
- Sound effects
- On-screen caption
- Transition to next scene

Rules:
- Total duration must match the script
- First scene = HOOK (most attention-grabbing)
- Last scene = CTA
- Visual descriptions should be cinematic and specific
- Camera movements: zoom_in, zoom_out, pan_left, pan_right, static, push_in, pull_out
- Transitions: fade, crossfade, slide_left, zoom, cut

Return ONLY valid JSON array of scenes:
[
    {
        "scene_number": 1,
        "duration": 3,
        "character": "character name or null",
        "dialogue": "dialogue text or null",
        "narration": "narration text",
        "visual_description": "detailed visual description",
        "camera": "zoom_in",
        "emotion": "excitement",
        "background": "modern office",
        "music_mood": "energetic",
        "sfx": "whoosh",
        "caption": "on-screen text",
        "transition": "fade"
    }
]"""

    def build_messages(self, input: AgentInput) -> list:
        script = input.content
        characters = input.context.get("characters", [])
        style = input.context.get("style", "cinematic")

        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a storyboard for this script:\n\n{script}\n\nStyle: {style}\nAvailable characters: {json.dumps(characters)}"},
        ]

    def parse_response(self, content: str) -> AgentOutput:
        data = parse_json(content)
        if data is None:
            return AgentOutput(content=content, structured_data={"scenes": []})
        if isinstance(data, list):
            scenes = data
        elif isinstance(data, dict):
            scenes = data.get("scenes", [data])
        else:
            scenes = []
        return AgentOutput(
            content=content,
            structured_data={"scenes": scenes if isinstance(scenes, list) else []},
        )
