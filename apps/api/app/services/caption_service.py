from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class CaptionEntry:
    index: int
    start_seconds: float
    end_seconds: float
    text: str
    word: Optional[str] = None


@dataclass
class CaptionStyle:
    font: str = "Arial"
    size: int = 48
    color: str = "#FFFFFF"
    background_color: Optional[str] = None
    position: str = "bottom"  # top, center, bottom
    animation: str = "pop"  # pop, fade, slide, highlight
    highlight_color: str = "#FFD700"
    outline_color: str = "#000000"
    outline_width: int = 2


PRESETS = {
    "minimal": CaptionStyle(font="Arial", size=42, color="#FFFFFF", animation="fade"),
    "comedy": CaptionStyle(font="Impact", size=56, color="#FFD700", highlight_color="#FF0000", animation="pop"),
    "meme": CaptionStyle(font="Impact", size=60, color="#FFFFFF", outline_color="#000000", outline_width=4, animation="pop"),
    "podcast": CaptionStyle(font="Georgia", size=38, color="#E0E0E0", position="bottom", animation="fade"),
    "gaming": CaptionStyle(font="monospace", size=44, color="#00FF00", highlight_color="#FF0000", animation="highlight"),
    "news": CaptionStyle(font="Arial", size=40, color="#FFFFFF", background_color="#CC0000", position="bottom", animation="slide"),
    "story": CaptionStyle(font="Georgia", size=46, color="#FFFFFF", highlight_color="#FFD700", animation="highlight"),
}


def generate_word_level_captions(
    text: str,
    total_duration: float,
    style: str = "minimal",
) -> List[CaptionEntry]:
    words = text.split()
    if not words:
        return []

    words_per_second = len(words) / total_duration
    captions = []

    for i, word in enumerate(words):
        start = i / words_per_second
        end = (i + 1) / words_per_second
        captions.append(CaptionEntry(
            index=i + 1,
            start_seconds=round(start, 3),
            end_seconds=round(end, 3),
            text=word,
            word=word,
        ))

    return captions


def captions_to_srt(captions: List[CaptionEntry]) -> str:
    srt_lines = []
    for cap in captions:
        start = _format_srt_time(cap.start_seconds)
        end = _format_srt_time(cap.end_seconds)
        srt_lines.append(f"{cap.index}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(cap.text)
        srt_lines.append("")
    return "\n".join(srt_lines)


def captions_to_ass(captions: List[CaptionEntry], style: CaptionStyle) -> str:
    ass_header = f"""[Script Info]
Title: AI Video Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{style.outline_width},2,2,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for cap in captions:
        start = _format_ass_time(cap.start_seconds)
        end = _format_ass_time(cap.end_seconds)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{cap.text}")

    return ass_header + "\n".join(events)


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
