"""Capability: ``normalize`` — produce a clean constant-frame-rate intermediate.

Real-world raw footage is variable-frame-rate with messy timestamps. Cutting it
directly desyncs audio. This step rebuilds a clean CFR file that every later step
can safely seek and cut. (Hard-won rule from production use.)
"""

from __future__ import annotations

from ..core.tool import Tool, ToolManifest, ToolResult
from ..core.context import RunContext
from .. import media


class NormalizeTool(Tool):
    manifest = ToolManifest(
        name="normalize_ffmpeg",
        capability="normalize",
        summary="Rebuild raw footage as a clean constant-frame-rate intermediate.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg", "ffprobe"),
    )

    def run(self, ctx: RunContext, *, input: str, fps: float | None = None) -> ToolResult:
        media.require("ffmpeg")
        src = input
        target_fps = fps or media.source_fps(src, default=float(ctx.config.encode.fps))
        out = ctx.paths.clips / "normalized.mov"

        media.run(
            [
                "ffmpeg", "-y", "-fflags", "+genpts", "-i", src,
                "-map", "0:v:0", "-map", "0:a:0",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-r", str(target_fps), "-fps_mode", "cfr",
                "-c:a", "pcm_s16le", "-ar", "48000",
                str(out),
            ],
            log=ctx.log,
            desc=f"normalize → CFR {target_fps}fps",
        )
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"fps": target_fps, "mean_volume_db": media.mean_volume_db(out)},
        )


TOOL = NormalizeTool()
