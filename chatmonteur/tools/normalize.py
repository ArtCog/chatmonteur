"""Capability: ``normalize`` — produce a clean constant-frame-rate intermediate.

Real-world raw footage is variable-frame-rate with messy timestamps. Cutting it
directly desyncs audio. This step rebuilds a clean CFR file that every later step
can safely seek and cut. (Hard-won rule from production use.)

It also loudness-normalises to the configured target (−14 LUFS) by default:
the silence threshold downstream (``cut_silence`` 0.14) is a fraction of peak
and is only valid on level-controlled audio — on a quiet recording it shreds
words. Pass ``loudness=False`` for flows that must cut RAW audio (e.g. the
separate-voice-track branch, where normalising before the cut destroys the
speech/pause gap — see skills/cutting.md Branch B).
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

    def run(self, ctx: RunContext, *, input: str, fps: float | None = None, loudness: bool = True) -> ToolResult:
        media.require("ffmpeg")
        src = input
        target_fps = fps or media.source_fps(src, default=float(ctx.config.encode.fps))
        out = ctx.paths.clips / "normalized.mov"

        # One-pass loudnorm here is Branch-A prep for the level-relative silence
        # threshold (two-pass linear is cleaner; tracked as a future upgrade).
        af = ["-af", f"loudnorm=I={ctx.config.encode.loudness_lufs}:TP=-1.5:LRA=11"] if loudness else []
        media.run(
            [
                "ffmpeg", "-y", "-fflags", "+genpts", "-i", src,
                # ALL audio tracks, not just the first: OBS records the mix on track 1
                # and the bare mic on track 2, and Branch B pause-cutting needs that
                # second track alive. '0:a?' keeps every one (and tolerates none).
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-r", str(target_fps), "-fps_mode", "cfr",
                *af,
                "-c:a", "pcm_s16le", "-ar", "48000",
                str(out),
            ],
            log=ctx.log,
            desc=f"normalize → CFR {target_fps}fps{', loudnorm −14' if loudness else ''}",
        )
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"fps": target_fps, "loudness": loudness, "mean_volume_db": media.mean_volume_db(out)},
        )


TOOL = NormalizeTool()
