import asyncio
import uuid
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from app.agents.registry import get_agent
from app.providers.llm.openai import OpenAIProvider
from app.providers.voice.providers import ElevenLabsProvider, MockVoiceProvider
from app.providers.image.providers import PollinationsProvider
from app.providers.video import get_video_provider
from app.services.render_service import VideoRenderer, RenderConfig, SceneAsset
from app.services.caption_service import generate_word_level_captions, captions_to_srt
from app.services.storage_service import get_storage, generate_asset_key
from app.config import settings


@dataclass
class PipelineResult:
    project_id: str
    status: str
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    script: Optional[Dict] = None
    scenes: Optional[list] = None
    captions_srt: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VideoPipeline:
    def __init__(self):
        self.llm = OpenAIProvider()
        self.voice = ElevenLabsProvider() if settings.elevenlabs_api_key else MockVoiceProvider()
        self.image = PollinationsProvider()
        self.video = get_video_provider()
        self.storage = get_storage()

    async def run(
        self,
        project_id: str,
        topic: str,
        duration: str = "30s",
        style: str = "educational",
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> PipelineResult:
        try:
            if on_progress:
                on_progress(0, "Starting pipeline...")

            if on_progress:
                on_progress(5, "Generating script...")
            script_agent = get_agent("script", self.llm)
            script_result = await script_agent.run({
                "content": topic,
                "context": {"duration": duration, "style": style}
            })
            script_data = script_result.structured_data or {}

            if on_progress:
                on_progress(15, "Planning storyboard...")
            storyboard_agent = get_agent("storyboard", self.llm)
            storyboard_result = await storyboard_agent.run({
                "content": script_data.get("full_script", topic),
                "context": {"characters": [], "style": style}
            })
            scenes_data = (storyboard_result.structured_data or {}).get("scenes", [])

            if on_progress:
                on_progress(30, "Generating scene visuals...")
            scene_assets = []
            for i, scene in enumerate(scenes_data):
                visual_desc = scene.get("visual_description", topic)
                images = await self.image.generate(
                    prompt=f"Cinematic, high quality: {visual_desc}",
                    size="1080x1920",
                )
                image_url = images[0].url if images else ""

                scene_assets.append(SceneAsset(
                    image_path=image_url,
                    duration=float(scene.get("duration", 3)),
                    transition=scene.get("transition", "fade"),
                ))

                if on_progress:
                    progress = 30 + (i + 1) / len(scenes_data) * 20
                    on_progress(progress, f"Generated visual {i + 1}/{len(scenes_data)}")

            if on_progress:
                on_progress(50, "Generating captions...")
            full_script = script_data.get("full_script", topic)
            total_duration = sum(s.duration for s in scene_assets)
            caption_entries = generate_word_level_captions(full_script, total_duration)
            srt_content = captions_to_srt(caption_entries)

            if on_progress:
                on_progress(60, "Rendering video...")
            renderer = VideoRenderer(RenderConfig(
                width=1080,
                height=1920,
                fps=30,
                preset="ultrafast",
            ))

            output_path = f"./storage/projects/{project_id}/rendered/video.mp4"
            render_result = await renderer.render(
                scenes=scene_assets,
                output_path=output_path,
                captions=caption_entries,
                on_progress=lambda p, m: on_progress(60 + p * 0.35, m) if on_progress else None,
            )

            if on_progress:
                on_progress(95, "Saving assets...")

            video_key = generate_asset_key(project_id, "video", "mp4")
            with open(render_result.output_path, "rb") as f:
                await self.storage.upload(f.read(), video_key, "video/mp4")

            if on_progress:
                on_progress(100, "Pipeline complete!")

            return PipelineResult(
                project_id=project_id,
                status="completed",
                video_path=render_result.output_path,
                script=script_data,
                scenes=scenes_data,
                captions_srt=srt_content,
                metadata={
                    "duration_seconds": render_result.duration,
                    "file_size": render_result.file_size,
                    "scene_count": len(scenes_data),
                    "caption_count": len(caption_entries),
                },
            )

        except Exception as e:
            return PipelineResult(
                project_id=project_id,
                status="failed",
                error=str(e),
            )
