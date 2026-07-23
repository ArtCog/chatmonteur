"""Capability: ``subtitles`` — build an SRT from a transcript and burn it in.

Takes a transcript JSON (from ``transcribe``), wraps it into readable lines, and
burns captions onto the video. Re-encodes (never stream-copies).
"""

from __future__ import annotations

import json
import pathlib

from ..core.context import RunContext
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media


class SubtitlesTool(Tool):
    manifest = ToolManifest(
        name="subtitles_ffmpeg",
        capability="subtitles",
        summary="Build SRT from transcript and burn captions with ffmpeg.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        transcript: str,
        max_chars: int = 42,
        burn: bool = True,
        font: str | None = None,
        font_dir: str | None = None,
    ) -> ToolResult:
        media.require("ffmpeg")
        font = font or _BRAND_FONT
        font_dir = font_dir or _BRAND_FONT_DIR
        data = json.loads(open(transcript, encoding="utf-8").read())
        srt_path = ctx.paths.transcripts / "captions.srt"
        srt_path.write_text(_to_srt(data, max_chars), encoding="utf-8")

        cues = sum(1 for s in data.get("segments", []) if s.get("text", "").strip())
        artifacts = {"srt": str(srt_path)}
        if burn and not cues:
            # Nothing to burn (e.g. silent/music clip) — pass the video through.
            ctx.log("subtitles: empty transcript, skipping burn")
            artifacts["video"] = str(input)
        elif burn:
            encoder = media.detect_encoder(ctx.config.encode.encoder)
            out = ctx.paths.clips / "subtitled.mp4"
            w, h = _video_wh(input)
            # ASS (not SRT+force_style): its header pins PlayResX/Y to the real
            # frame, so FontSize/margins are REAL PIXELS. SRT+force_style is scaled
            # by libass's default 288 PlayResY → a giant caption. (Learned the hard way.)
            ass_path = ctx.paths.transcripts / "captions.ass"
            ass_path.write_text(_to_ass(data, max_chars, w, h, font), encoding="utf-8")
            artifacts["ass"] = str(ass_path)
            fd = f":fontsdir='{media.filter_path(font_dir)}'" if font_dir else ""
            # Run from the ASS's folder, reference by bare name (dodge drive colon).
            media.run(
                [
                    "ffmpeg", "-y", "-i", str(input),
                    "-vf", f"ass={ass_path.name}{fd},format=yuv420p",
                    "-c:v", encoder, *media.encoder_quality_args(encoder),
                    "-pix_fmt", "yuv420p",
                    "-c:a", "copy",
                    str(out),
                ],
                log=ctx.log,
                desc=f"burn subtitles ({font}, {h}p)",
                cwd=ass_path.parent,
            )
            artifacts["video"] = str(out)
        return ToolResult(artifacts=artifacts, meta={"cues": data and len(data.get("segments", []))})


# --- THE STANDARD --------------------------------------------------------------
# GEOMETRY (agreed in the tuner): size/position as a fraction of frame height so
# they hold at any resolution. STYLE (font/colour/plate): from the brand kit
# «ИИмерсивный - Mono» — Golos Text Bold, paper-white on a semi-transparent scrim
# (design "C · чисто" — the default caption). Mirrors skills/subtitles.md +
# assets/brand/default/brand.md. To retune: change these constants only.
_SIZE_FRAC = 0.05     # font size = 5% of frame height
_MARGIN_FRAC = 0.09   # bottom margin = 9% of frame height (above player controls)
_WIDTH_FRAC = 0.80    # text area = 80% of frame width (L+R margins take the rest)

# Brand colours as ASS BGR (&HAABBGGRR; AA alpha: 00 opaque … FF transparent).
_PAPER_BGR = "&H00F7FAFA"    # paper #FAFAF7 — caption text
_SCRIM_BGR = "&H7A0A0908"    # scrim rgba(8,9,10,.52) → ink #08090A @ ~48% alpha
_BRAND_FONT = "Golos Text"
# Bundled brand fonts (Golos/JetBrains/Playfair, OFL) — libass finds them by family.
_BRAND_FONT_DIR = str(pathlib.Path(__file__).resolve().parents[2] / "assets" / "brand" / "default" / "fonts")


def _video_wh(path: str) -> tuple[int, int]:
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            return int(s.get("width", 1920)), int(s["height"])
    return 1920, 1080


def _video_wh(path: str) -> tuple[int, int]:
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            return int(s.get("width", 1920)), int(s["height"])
    return 1920, 1080


def _to_ass(data: dict, max_chars: int, width: int, height: int, font: str) -> str:
    """ASS with PlayRes pinned to the real frame → FontSize/margins are real px.

    Brand style «Mono»: Golos Text Bold, paper text on a semi-transparent scrim
    (BorderStyle=4 = box in BackColour), fixed bottom-center anchor.
    """
    fs = round(_SIZE_FRAC * height)
    mv = round(_MARGIN_FRAC * height)
    pad = max(6, round(0.010 * height))  # scrim padding around text
    side = round((1 - _WIDTH_FRAC) / 2 * width)  # L/R margin → 80% text width
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        f"PlayResX: {width}\nPlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Bold=-1; Alignment 2 = bottom-center (fixed); BorderStyle 4 = box in
        # BackColour (the scrim); Outline = box padding; Shadow 0.
        f"Style: Default,{font},{fs},{_PAPER_BGR},{_PAPER_BGR},{_SCRIM_BGR},{_SCRIM_BGR},"
        f"-1,0,0,0,100,100,0,0,4,{pad},0,2,{side},{side},{mv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for start, end, text in _build_cues(data, max_chars):
        body = _wrap(text, max_chars).replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{body}")
    return header + "\n".join(lines) + "\n"


def _ass_time(t: float) -> str:
    t = max(t, 0.0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):d}:{int(m):02d}:{s:05.2f}"


def _fmt(t: float) -> str:
    h, rem = divmod(max(t, 0.0), 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def _wrap(text: str, max_chars: int) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _chunk_words(words: list[dict], max_chars: int, max_dur: float = 2.8, max_lines: int = 2):
    """Group word-timestamps into short caption cues (talking-head style).

    Breaks on sentence punctuation, ~max_chars*max_lines length, or max_dur — so
    captions are short phrases, not one giant block per whisper segment.
    """
    cues, cur = [], []
    for w in words:
        cur.append(w)
        text = "".join(x.get("word", "") for x in cur).strip()
        dur = float(cur[-1]["end"]) - float(cur[0]["start"])
        if len(text) >= max_chars * max_lines or dur >= max_dur or text.endswith((".", "!", "?", "…")):
            cues.append((float(cur[0]["start"]), float(cur[-1]["end"]), text))
            cur = []
    if cur:
        text = "".join(x.get("word", "") for x in cur).strip()
        cues.append((float(cur[0]["start"]), float(cur[-1]["end"]), text))
    return cues


def _build_cues(data: dict, max_chars: int) -> list[tuple[float, float, str]]:
    """Segment a transcript into short caption cues (shared by SRT + ASS)."""
    cues: list[tuple[float, float, str]] = []
    for seg in data.get("segments", []):
        words = seg.get("words")
        if words:
            cues.extend(_chunk_words(words, max_chars))
        elif seg.get("text", "").strip():
            cues.append((float(seg["start"]), float(seg["end"]), seg["text"].strip()))
    return cues


def _to_srt(data: dict, max_chars: int) -> str:
    out = []
    for i, (start, end, text) in enumerate(_build_cues(data, max_chars), start=1):
        wrapped = _wrap(text, max_chars)
        if wrapped:
            out.append(f"{i}\n{_fmt(start)} --> {_fmt(end)}\n{wrapped}\n")
    return "\n".join(out)


TOOL = SubtitlesTool()
