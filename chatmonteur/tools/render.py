"""Capability: ``render`` — delivery-quality encode.

Auto-detects a working encoder (NVENC/QSV/VideoToolbox/libx264), scales to the
configured height, and applies loudness normalisation as the LAST audio step.
Never stream-copies. This step makes the media technically suitable for
delivery; editorial approval and media rights remain separate gates.

Loudness is measured first, then applied — the two-pass form. One-pass loudnorm
has to guess the programme level as it goes, so it rides the gain and compresses
the dialogue; handed the measured numbers it becomes a straight linear shift to
the target instead. This is the only place in the pipeline that sets loudness
(``normalize`` levels the audio with a plain gain, on purpose).
"""

from __future__ import annotations

import json
import re

from ..core.tool import Tool, ToolManifest, ToolResult
from ..core.context import RunContext
from ..core.errors import ToolError
from .. import media


_MEASURED = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def _loudnorm_filter(src: str, lufs: float, *, log) -> str:
    """Measure the input, then return a loudnorm that only shifts the level.

    Falls back to the one-pass form if measurement fails (an unreadable or
    silent track) — a slightly compressed render beats no render, and the
    fallback is logged rather than hidden.
    """
    base = f"loudnorm=I={lufs}:TP=-1.5:LRA=11"
    stats = _measure(src, base, log=log)
    if not stats:
        log("render: loudness measurement failed — falling back to one-pass loudnorm")
        return base
    measured = ":".join(f"{k.replace('input_', 'measured_')}={stats[k]}" for k in _MEASURED[:4])
    # linear=true is the request; ffmpeg silently drops back to the dynamic mode
    # when the source cannot reach the target linearly, which is the right call.
    return f"{base}:{measured}:offset={stats['target_offset']}:linear=true"


def _measure(src: str, base: str, *, log) -> dict[str, str]:
    try:
        proc = media.run(
            ["ffmpeg", "-hide_banner", "-i", src, "-vn",
             "-af", f"{base}:print_format=json", "-f", "null", "-"],
            log=log, desc="measure loudness (pass 1 of 2)",
        )
    except ToolError:
        return {}          # caller logs and falls back to one-pass
    # The JSON block is the last {...} ffmpeg prints on stderr.
    blocks = re.findall(r"\{[^{}]*\}", proc.stderr or "", re.S)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if all(k in data for k in _MEASURED):
            return {k: str(data[k]) for k in _MEASURED}
    return {}


class RenderTool(Tool):
    manifest = ToolManifest(
        name="render_ffmpeg",
        capability="render",
        summary="Delivery-quality encode with auto-detected encoder + loudnorm (cross-platform).",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
    )

    def run(self, ctx: RunContext, *, input: str, name: str = "rendered.mp4", preview: bool = False) -> ToolResult:
        media.require("ffmpeg")
        enc_cfg = ctx.config.encode
        encoder = "libx264" if preview else media.detect_encoder(enc_cfg.encoder)
        height = 720 if preview else enc_cfg.final_height
        out_dir = ctx.paths.previews if preview else ctx.paths.renders
        out = out_dir / name

        # format=yuv420p is mandatory for a deliverable: players/YouTube reject
        # 4:4:4 / gbrp (which lut3d upstream can introduce). -ar 48000 resets the
        # samplerate loudnorm bumps to a non-standard value.
        vf = f"scale=-2:{height}:flags=lanczos,format=yuv420p"
        # loudnorm sets the level; a true-peak limiter after it catches the
        # inter-sample peaks loudnorm leaves behind (measured up to −1.3 dBFS on
        # real footage → clipping risk). limit=0.75 ≈ −2.5 dBTP.
        af = (
            f"{_loudnorm_filter(input, enc_cfg.loudness_lufs, log=ctx.log)},"
            "alimiter=limit=0.75:level=false:attack=3:release=30"
        )
        cmd = [
            "ffmpeg", "-y", "-i", input,
            "-vf", vf,
            "-c:v", encoder, *media.encoder_quality_args(encoder),
            "-pix_fmt", "yuv420p",
            "-af", af,
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000",  # 256k floor for speech
            "-movflags", "+faststart",
            str(out),
        ]
        media.run(cmd, log=ctx.log, desc=f"render → {encoder} {height}p{' (preview)' if preview else ''}")

        level = media.mean_volume_db(out)
        if level is not None and level < -60:
            # Correctness guard: a finished file should not be effectively silent.
            ctx.log(f"⚠ output mean volume {level} dBFS looks silent — check audio mapping")
        return ToolResult(artifacts={"video": str(out)}, meta={"encoder": encoder, "mean_volume_db": level})


TOOL = RenderTool()
