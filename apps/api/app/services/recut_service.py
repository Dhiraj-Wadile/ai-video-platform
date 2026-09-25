import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.job import RenderJob
from app.models.script import Scene, Script
from app.services.caption_service import generate_word_level_captions, captions_to_srt, CaptionEntry
from app.services.render_service import VideoRenderer, RenderConfig, SceneAsset
from app.services.storage_service import get_storage, generate_asset_key


async def _resolve_image_local(url: str, storage, tmp_dir: str) -> Optional[str]:
    if url.startswith("/storage/"):
        base = getattr(storage, "base_dir", "./storage")
        path = os.path.join(base, url[len("/storage/"):])
        return path if os.path.exists(path) else None
    if url.startswith("http://") or url.startswith("https://"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            path = os.path.join(tmp_dir, os.path.basename(url.split("?")[0]) or "image.png")
            with open(path, "wb") as f:
                f.write(resp.content)
            return path
        except Exception:
            return None
    return url if os.path.exists(url) else None


class RecutService:
    def __init__(self, renderer=None, storage=None, render_config: Optional[RenderConfig] = None):
        self.renderer = renderer
        self.storage = storage or get_storage()
        self.render_config = render_config or RenderConfig(preset="ultrafast")

    def _ensure_renderer(self) -> VideoRenderer:
        if self.renderer is None:
            self.renderer = VideoRenderer(self.render_config)
        return self.renderer

    async def _latest_scene_image(self, db: AsyncSession, project_id: str) -> Dict[int, str]:
        result = await db.execute(
            select(Asset)
            .where(Asset.project_id == project_id, Asset.type == "scene_image")
            .order_by(Asset.created_at.desc())
        )
        latest: Dict[int, str] = {}
        for asset in result.scalars().all():
            scene_id = (asset.metadata_json or {}).get("scene_id")
            if scene_id is not None and scene_id not in latest:
                latest[int(scene_id)] = asset.url
        return latest

    async def recut(self, project_id: str, db: AsyncSession) -> RenderJob:
        scenes_rows = (await db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_number.asc())
        )).scalars().all()
        if not scenes_rows:
            raise ValueError("Project has no scenes to render")

        script_row = (await db.execute(
            select(Script).where(Script.project_id == project_id).order_by(Script.created_at.desc()).limit(1)
        )).scalar_one_or_none()

        images = await self._latest_scene_image(db, project_id)

        tmp_dir = tempfile.mkdtemp(prefix="ai_video_recut_")
        scene_assets: list[SceneAsset] = []
        for scene in scenes_rows:
            url = images.get(scene.scene_number)
            if not url:
                raise ValueError(f"Scene {scene.scene_number} has no visual asset; regenerate it first")
            local = await _resolve_image_local(url, self.storage, tmp_dir)
            if not local:
                raise ValueError(f"Scene {scene.scene_number} visual could not be resolved to a file")
            scene_assets.append(SceneAsset(
                image_path=local,
                duration=float(scene.duration or 3),
                transition=scene.transition or "fade",
            ))

        caption_entries: list[CaptionEntry] = []
        if script_row:
            full_script = script_row.content or ""
            total_duration = sum(sa.duration for sa in scene_assets)
            caption_entries = generate_word_level_captions(full_script, total_duration)

        job = RenderJob(project_id=project_id, status="rendering", progress=10, progress_message="Recutting scenes...")
        db.add(job)
        await db.flush()

        output_key = generate_asset_key(project_id, "video", "mp4")
        output_path = os.path.join(tmp_dir, "recut.mp4")

        renderer = self._ensure_renderer()
        result = await renderer.render(
            scenes=scene_assets,
            output_path=output_path,
            captions=caption_entries or None,
            on_progress=lambda p, m: None,
        )

        with open(result.output_path, "rb") as f:
            await self.storage.upload(f.read(), output_key, "video/mp4")
        video_url = await self.storage.get_url(output_key)

        db.add(Asset(
            project_id=project_id,
            type="video",
            url=video_url,
            metadata_json={
                "key": output_key,
                "duration_seconds": result.duration,
                "file_size": result.file_size,
                "source": "recut",
            },
        ))

        srt_content = captions_to_srt(caption_entries) if caption_entries else ""
        if srt_content:
            srt_key = output_key.replace(".mp4", ".srt")
            await self.storage.upload(srt_content.encode("utf-8"), srt_key, "text/plain")
            db.add(Asset(
                project_id=project_id,
                type="captions",
                url=await self.storage.get_url(srt_key),
                metadata_json={"content": srt_content, "source": "recut"},
            ))

        job.status = "completed"
        job.progress = 100
        job.progress_message = "Re-render complete"
        job.output_url = video_url
        job.completed_at = datetime.now(timezone.utc)
        return job