from typing import Dict, List, Optional, Type

from app.providers.base import ProviderTask, ProviderNotConfigured, ProviderInfo
from app.providers.llm.openai import OpenAIProvider
from app.providers.image.providers import PollinationsProvider
from app.providers.voice.providers import ElevenLabsProvider, MockVoiceProvider
from app.providers.video import PollinationsVideoProvider, RunwayVideoProvider
from app.providers.video.higgsfield import HiggsfieldVideoProvider


PROVIDER_REGISTRY: Dict[ProviderTask, List[Type]] = {
    ProviderTask.LLM: [OpenAIProvider],
    ProviderTask.IMAGE: [PollinationsProvider],
    ProviderTask.VOICE: [ElevenLabsProvider, MockVoiceProvider],
    ProviderTask.VIDEO: [HiggsfieldVideoProvider, RunwayVideoProvider, PollinationsVideoProvider],
}


class ProviderRouter:
    def candidates(self, task: ProviderTask) -> List[Type]:
        return list(PROVIDER_REGISTRY.get(task, []))

    def available(self, task: ProviderTask) -> List[Type]:
        return [cls for cls in self.candidates(task) if cls.is_configured()]

    def resolve_all(self) -> Dict[ProviderTask, object]:
        return {
            task: self.resolve(task)
            for task in (ProviderTask.LLM, ProviderTask.IMAGE, ProviderTask.VOICE, ProviderTask.VIDEO)
        }

    def resolve(self, task: ProviderTask, name: Optional[str] = None) -> object:
        candidates = self.candidates(task)

        if name is not None:
            for cls in candidates:
                if cls.name == name:
                    if cls.is_configured():
                        return cls()
                    raise ProviderNotConfigured(task, [name])
            raise ProviderNotConfigured(task, [name])

        enabled = self.available(task)
        if not enabled:
            raise ProviderNotConfigured(task, [cls.name for cls in candidates])

        best = sorted(enabled, key=lambda cls: (cls.is_mock, cls.priority))[0]
        return best()

    def inventory(self) -> List[ProviderInfo]:
        infos = []
        for task, classes in PROVIDER_REGISTRY.items():
            infos.extend(cls.to_info() for cls in classes)
        return infos

    def as_dicts(self) -> list:
        return [info.as_dict() for info in self.inventory()]


provider_router = ProviderRouter()


def get_provider(task: ProviderTask, name: Optional[str] = None):
    return provider_router.resolve(task, name=name)