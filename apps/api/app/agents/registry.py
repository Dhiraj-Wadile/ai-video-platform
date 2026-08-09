from typing import Dict, Type
from app.agents.base import BaseAgent
from app.agents.trend_agent import TrendAgent
from app.agents.script_agent import ScriptAgent
from app.agents.storyboard_agent import StoryboardAgent
from app.agents.character_agent import CharacterAgent
from app.agents.quality_agent import QualityAgent


AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "trend": TrendAgent,
    "script": ScriptAgent,
    "storyboard": StoryboardAgent,
    "character": CharacterAgent,
    "quality": QualityAgent,
}


def get_agent(name: str, llm_provider) -> BaseAgent:
    agent_class = AGENT_REGISTRY.get(name)
    if not agent_class:
        raise ValueError(f"Unknown agent: {name}")
    return agent_class(llm_provider)


def list_agents() -> list:
    return [
        {"name": name, "description": cls.description}
        for name, cls in AGENT_REGISTRY.items()
    ]
