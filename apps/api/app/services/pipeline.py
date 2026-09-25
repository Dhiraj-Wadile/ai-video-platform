from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import inspect
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.registry import get_agent
from app.providers.router import provider_router, ProviderTask
from app.services.render_service import VideoRenderer, RenderConfig, SceneAsset
from app.services.caption_service import generate_word_level_captions, captions_to_srt
from app.services.storage_service import get_storage, generate_asset_key
from app.models.project import Project
from app.models.script import Script, Scene
from app.models.job import GenerationJob
from app.models.asset import Asset
from app.models.lineage import GenerationRecord


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
    _TASKS = (
        ProviderTask.LLM,
        ProviderTask.IMAGE,
        ProviderTask.VOICE,
        ProviderTask.VIDEO,
    )

    def __init__(self):
        self.providers = provider_router.resolve_all()
        self.llm = self.providers[ProviderTask.LLM]
        self.image = self.providers[ProviderTask.IMAGE]
        self.voice = self.providers[ProviderTask.VOICE]
        self.video = self.providers[ProviderTask.VIDEO]
        self.storage = get_storage()
        self.providers_metadata = {
            task.value: {
                "name": getattr(self.providers[task], "name", type(self.providers[task]).__name__),
                "model": getattr(self.providers[task], "default_model", None),
            }
            for task in self._TASKS
        }

    async def run(
        self,
        project_id: str,
        topic: str,
        duration: str = "30s",
        style: str = "educational",
        db: Optional[AsyncSession] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> PipelineResult:
        project = None
        script_id = None
        script_record_id = None
        storyboard_record_id = None

        try:
            if db:
                project_row = await db.execute(select(Project).where(Project.id == project_id))
                project = project_row.scalar_one_or_none()
                if project:
                    project.status = "generating"
                    await db.commit()

            await self._emit_progress(on_progress, 0, "Starting pipeline...")

            await self._emit_progress(on_progress, 5, "Generating script...")
            script_agent = get_agent("script", self.llm)
            script_result = await script_agent.run({
                "content": topic,
                "context": {"duration": duration, "style": style}
            })
            script_data = script_result.structured_data or {}

            if db and project:
                script = Script(
                    project_id=project_id,
                    title=script_data.get("title", topic),
                    content=script_data.get("full_script", script_result.content),
                    duration=script_data.get("duration"),
                    structure_json=script_data.get("sections"),
                )
                db.add(script)
                await db.flush()
                script_id = str(script.id)
                db.add(self._generation_job(project_id, "script", script_result, topic))
                script_record = self._lineage_record(
                    project_id,
                    task=ProviderTask.LLM,
                    provider=self._provider_label(self.providers[ProviderTask.LLM]),
                    model=script_result.metadata.get("model"),
                    cost_cents=script_result.metadata.get("cost_cents"),
                    latency_ms=script_result.metadata.get("latency_ms"),
                    context={"agent": "script", "title": script_data.get("title", topic)},
                )
                db.add(script_record)
                await db.flush()
                script_record_id = str(script_record.id)
                await db.commit()

            await self._emit_progress(on_progress, 15, "Planning storyboard...")
            storyboard_agent = get_agent("storyboard", self.llm)
            storyboard_result = await storyboard_agent.run({
                "content": script_data.get("full_script", topic),
                "context": {"characters": [], "style": style}
            })
            scenes_data = (storyboard_result.structured_data or {}).get("scenes", [])

            if db and project:
                for i, scene in enumerate(scenes_data, start=1):
                    db.add(Scene(
                        project_id=project_id,
                        script_id=script_id,
                        scene_number=int(scene.get("scene_number", i)),
                        duration=int(scene.get("duration", 3)),
                        narration=scene.get("narration"),
                        visual_description=scene.get("visual_description"),
                        camera=scene.get("camera"),
                        emotion=scene.get("emotion"),
                        background=scene.get("background"),
                        music_mood=scene.get("music_mood"),
                        sfx=scene.get("sfx"),
                        caption=scene.get("caption"),
                        transition=scene.get("transition"),
                    ))
                db.add(self._generation_job(project_id, "storyboard", storyboard_result, topic))
                storyboard_record = self._lineage_record(
                    project_id,
                    task=ProviderTask.LLM,
                    provider=self._provider_label(self.providers[ProviderTask.LLM]),
                    model=storyboard_result.metadata.get("model"),
                    cost_cents=storyboard_result.metadata.get("cost_cents"),
                    latency_ms=storyboard_result.metadata.get("latency_ms"),
                    context={"agent": "storyboard", "scene_count": len(scenes_data)},
                    parent_id=script_record_id,
                )
                db.add(storyboard_record)
                await db.flush()
                storyboard_record_id = str(storyboard_record.id)
                await db.commit()

            await self._emit_progress(on_progress, 30, "Generating scene visuals...")
            scene_assets = []
            for i, scene in enumerate(scenes_data):
                visual_desc = scene.get("visual_description", topic)
                image_start = time.time()
                images = await self.image.generate(
                    prompt=f"Cinematic, high quality: {visual_desc}",
                    size="1080x1920",
                )
                image_latency = int((time.time() - image_start) * 1000)
                image_url = images[0].url if images else ""

                scene_assets.append(SceneAsset(
                    image_path=image_url,
                    duration=float(scene.get("duration", 3)),
                    transition=scene.get("transition", "fade"),
                ))

                if db and project:
                    scene_number = int(scene.get("scene_number", i + 1))
                    db.add(Asset(
                        project_id=project_id,
                        type="scene_image",
                        url=image_url if image_url else f"/storage/projects/{project_id}/scene/{scene_number}.png",
                        metadata_json={
                            "scene_id": scene_number,
                            "source": "pipeline",
                            "key": generate_asset_key(project_id, "scene_image", "png"),
                        },
                    ))
                    image_record = self._lineage_record(
                        project_id,
                        task=ProviderTask.IMAGE,
                        provider=self._provider_label(self.providers[ProviderTask.IMAGE]),
                        model=getattr(self.providers[ProviderTask.IMAGE], "default_model", None),
                        cost_cents=0,
                        latency_ms=image_latency,
                        context={"scene_id": scene_number, "prompt": visual_desc},
                        parent_id=storyboard_record_id,
                    )
                    db.add(image_record)
                    await db.flush()
                    await db.commit()

                await self._emit_progress(
                    on_progress,
                    30 + (i + 1) / len(scenes_data) * 20,
                    f"Generated visual {i + 1}/{len(scenes_data)}",
                )

            await self._emit_progress(on_progress, 50, "Generating captions...")
            full_script = script_data.get("full_script", topic)
            total_duration = sum(s.duration for s in scene_assets)
            caption_entries = generate_word_level_captions(full_script, total_duration)
            srt_content = captions_to_srt(caption_entries)

            await self._emit_progress(on_progress, 60, "Rendering video...")
            renderer = VideoRenderer(RenderConfig(
                width=1080,
                height=1920,
                fps=30,
                preset="ultrafast",
            ))

            output_path = f"./storage/projects/{project_id}/rendered/video.mp4"

            async def _render_progress(p: float, m: str):
                await self._emit_progress(on_progress, 60 + p * 0.35, m)

            render_result = await renderer.render(
                scenes=scene_assets,
                output_path=output_path,
                captions=caption_entries,
                on_progress=_render_progress,
            )

            await self._emit_progress(on_progress, 95, "Saving assets...")

            video_key = generate_asset_key(project_id, "video", "mp4")
            with open(render_result.output_path, "rb") as f:
                await self.storage.upload(f.read(), video_key, "video/mp4")

            if db and project:
                video_url = await self.storage.get_url(video_key)
                db.add(Asset(
                    project_id=project_id,
                    type="video",
                    url=video_url,
                    metadata_json={
                        "key": video_key,
                        "duration_seconds": render_result.duration,
                        "file_size": render_result.file_size,
                    },
                ))
                db.add(Asset(
                    project_id=project_id,
                    type="captions",
                    url=await self.storage.get_url(video_key.replace(".mp4", ".srt")),
                    metadata_json={"content": srt_content},
                ))
                db.add(self._lineage_record(
                    project_id,
                    task="render",
                    provider="local-ffmpeg",
                    model=None,
                    cost_cents=0,
                    latency_ms=0,
                    context={"duration_seconds": render_result.duration, "file_size": render_result.file_size},
                    parent_id=storyboard_record_id,
                ))
                project.status = "ready"
                await db.commit()

            await self._emit_progress(on_progress, 100, "Pipeline complete!")

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
                    "providers": self.providers_metadata,
                },
            )

        except Exception as e:
            if db and project:
                project.status = "failed"
                await db.commit()
            return PipelineResult(
                project_id=project_id,
                status="failed",
                error=str(e),
            )

    @staticmethod
    async def _emit_progress(on_progress, progress: float, message: str):
        if on_progress is None:
            return
        if inspect.iscoroutinefunction(on_progress):
            await on_progress(progress, message)
        else:
            on_progress(progress, message)

    @staticmethod
    def _provider_label(provider) -> str:
        return getattr(provider, "name", None) or type(provider).__name__

    @staticmethod
    def _generation_job(project_id: str, agent_name: str, result, input_hint: str) -> GenerationJob:
        metadata = result.metadata or {}
        return GenerationJob(
            project_id=project_id,
            agent_name=agent_name,
            status="completed",
            input_json={"topic": input_hint},
            output_json=result.structured_data,
            model=metadata.get("model"),
            tokens_in=metadata.get("tokens_in"),
            tokens_out=metadata.get("tokens_out"),
            latency_ms=metadata.get("latency_ms"),
            cost_cents=metadata.get("cost_cents"),
        )

    @staticmethod
    def _lineage_record(
        project_id: str,
        task,
        provider: str,
        model,
        cost_cents,
        latency_ms,
        context: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> GenerationRecord:
        return GenerationRecord(
            project_id=project_id,
            task=task.value if hasattr(task, "value") else str(task),
            provider=provider,
            model=model,
            status="completed",
            cost_cents=cost_cents or 0,
            latency_ms=latency_ms or 0,
            parent_id=parent_id,
            context_json=context,
        )
