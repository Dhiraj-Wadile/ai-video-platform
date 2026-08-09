import os
import subprocess
import tempfile
import uuid
from typing import List, Optional, Callable
from dataclasses import dataclass
import asyncio

from app.services.caption_service import CaptionEntry, captions_to_srt


@dataclass
class RenderConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    format: str = "mp4"
    codec: str = "libx264"
    preset: str = "medium"
    crf: int = 23
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"


@dataclass
class SceneAsset:
    image_path: str
    duration: float
    narration_audio_path: Optional[str] = None
    transition: str = "fade"
    transition_duration: float = 0.5


@dataclass
class RenderResult:
    output_path: str
    duration: float
    file_size: int
    format: str


class VideoRenderer:
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        self.temp_dir = tempfile.mkdtemp(prefix="ai_video_render_")
        self._ensure_ffmpeg()

    def _ensure_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except FileNotFoundError:
            raise RuntimeError("FFmpeg is not installed or not in PATH")

    async def render(
        self,
        scenes: List[SceneAsset],
        output_path: str,
        background_music_path: Optional[str] = None,
        music_volume: float = 0.15,
        captions: Optional[List[CaptionEntry]] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> RenderResult:
        job_id = str(uuid.uuid4())[:8]
        slides_dir = os.path.join(self.temp_dir, f"slides_{job_id}")
        os.makedirs(slides_dir, exist_ok=True)

        try:
            if on_progress:
                on_progress(0, "Preparing slides...")

            slide_paths = []
            for i, scene in enumerate(scenes):
                slide_path = os.path.join(slides_dir, f"slide_{i:03d}.png")
                await self._create_slide(scene.image_path, scene.duration, slide_path, i, len(scenes))
                slide_paths.append(slide_path)
                if on_progress:
                    on_progress((i + 1) / len(scenes) * 20, f"Created slide {i + 1}/{len(scenes)}")

            if on_progress:
                on_progress(20, "Building video timeline...")

            video_parts = await self._build_video_parts(slide_paths, scenes, job_id)

            if on_progress:
                on_progress(40, "Concatenating video...")

            concatenated = await self._concatenate_videos(video_parts, job_id)

            if on_progress:
                on_progress(55, "Adding audio...")

            with_audio = await self._add_audio(concatenated, scenes, job_id)

            if background_music_path and os.path.exists(background_music_path):
                if on_progress:
                    on_progress(70, "Mixing background music...")
                with_audio = await self._mix_music(with_audio, background_music_path, music_volume, job_id)

            if captions:
                if on_progress:
                    on_progress(80, "Burning captions...")
                srt_path = os.path.join(self.temp_dir, f"captions_{job_id}.srt")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(captions_to_srt(captions))
                with_audio = await self._burn_captions(with_audio, srt_path, job_id)

            if on_progress:
                on_progress(90, "Finalizing...")

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if with_audio != output_path:
                os.rename(with_audio, output_path)

            file_size = os.path.getsize(output_path)
            total_duration = sum(s.duration for s in scenes)

            if on_progress:
                on_progress(100, "Render complete!")

            return RenderResult(
                output_path=output_path,
                duration=total_duration,
                file_size=file_size,
                format=self.config.format,
            )

        finally:
            self._cleanup(slides_dir)

    async def _create_slide(
        self,
        image_path: str,
        duration: float,
        output_path: str,
        index: int,
        total: int,
    ):
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", str(duration),
            "-framerate", str(self.config.fps),
            "-i", image_path,
            "-vf", f"scale={self.config.width}:{self.config.height}:force_original_aspect_ratio=decrease,pad={self.config.width}:{self.config.height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-frames:v", str(int(duration * self.config.fps)),
            output_path,
        ]
        await self._run_ffmpeg(cmd)

    async def _build_video_parts(
        self,
        slide_paths: List[str],
        scenes: List[SceneAsset],
        job_id: str,
    ) -> List[str]:
        parts = []
        for i, (slide_path, scene) in enumerate(zip(slide_paths, scenes)):
            part_path = os.path.join(self.temp_dir, f"part_{job_id}_{i:03d}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", str(scene.duration),
                "-framerate", str(self.config.fps),
                "-i", slide_path,
                "-c:v", self.config.codec,
                "-preset", self.config.preset,
                "-crf", str(self.config.crf),
                "-pix_fmt", "yuv420p",
                part_path,
            ]
            await self._run_ffmpeg(cmd)
            parts.append(part_path)
        return parts

    async def _concatenate_videos(self, parts: List[str], job_id: str) -> str:
        concat_file = os.path.join(self.temp_dir, f"concat_{job_id}.txt")
        with open(concat_file, "w") as f:
            for part in parts:
                f.write(f"file '{part}'\n")

        output = os.path.join(self.temp_dir, f"concat_{job_id}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output,
        ]
        await self._run_ffmpeg(cmd)
        return output

    async def _add_audio(self, video_path: str, scenes: List[SceneAsset], job_id: str) -> str:
        audio_paths = [s.narration_audio_path for s in scenes if s.narration_audio_path]
        if not audio_paths:
            return video_path

        merged_audio = os.path.join(self.temp_dir, f"audio_{job_id}.mp3")
        concat_audio = os.path.join(self.temp_dir, f"audio_concat_{job_id}.txt")
        with open(concat_audio, "w") as f:
            for ap in audio_paths:
                f.write(f"file '{ap}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_audio,
            "-c", "copy",
            merged_audio,
        ]
        await self._run_ffmpeg(cmd)

        output = os.path.join(self.temp_dir, f"video_audio_{job_id}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", merged_audio,
            "-c:v", "copy",
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-shortest",
            output,
        ]
        await self._run_ffmpeg(cmd)
        return output

    async def _mix_music(self, video_path: str, music_path: str, volume: float, job_id: str) -> str:
        output = os.path.join(self.temp_dir, f"video_music_{job_id}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            output,
        ]
        await self._run_ffmpeg(cmd)
        return output

    async def _burn_captions(self, video_path: str, srt_path: str, job_id: str) -> str:
        output = os.path.join(self.temp_dir, f"video_captions_{job_id}.mp4")
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
            "-c:v", self.config.codec,
            "-preset", self.config.preset,
            "-crf", str(self.config.crf),
            "-c:a", "copy",
            output,
        ]
        await self._run_ffmpeg(cmd)
        return output

    async def _run_ffmpeg(self, cmd: List[str]):
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()[-500:]}")

    def _cleanup(self, slides_dir: str):
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
