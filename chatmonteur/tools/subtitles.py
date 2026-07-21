"""Capability: ``subtitles`` — build an SRT from a transcript and burn it in.

Takes a transcript JSON (from ``transcribe``), wraps it into readable lines, and
burns captions onto the video. Re-encodes (never stream-copies).
"""

from __future__ import annotations

import json

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

    def run(self, ctx: RunContext, *, input: str, transcript: str, max_chars: int = 42, burn: bool = True) -> ToolResult:
        media.require("ffmpeg")
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
            # Run from the SRT's folder and reference it by bare name, so the
            # filter never sees a Windows drive colon.
            media.run(
                [
                    "ffmpeg", "-y", "-i", str(input),
                    "-vf", f"subtitles={srt_path.name},format=yuv420p",
                    "-c:v", encoder, *media.encoder_quality_args(encoder),
                    "-pix_fmt", "yuv420p",
                    "-c:a", "copy",
                    str(out),
                ],
                log=ctx.log,
                desc="burn subtitles",
                cwd=srt_path.parent,
            )
            artifacts["video"] = str(out)
        return ToolResult(artifacts=artifacts, meta={"cues": data and len(data.get("segments", []))})


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


def _to_srt(data: dict, max_chars: int) -> str:
    cues: list[tuple[float, float, str]] = []
    for seg in data.get("segments", []):
        words = seg.get("words")
        if words:
            cues.extend(_chunk_words(words, max_chars))
        elif seg.get("text", "").strip():
            cues.append((float(seg["start"]), float(seg["end"]), seg["text"].strip()))

    out = []
    for i, (start, end, text) in enumerate(cues, start=1):
        wrapped = _wrap(text, max_chars)
        if wrapped:
            out.append(f"{i}\n{_fmt(start)} --> {_fmt(end)}\n{wrapped}\n")
    return "\n".join(out)


TOOL = SubtitlesTool()
