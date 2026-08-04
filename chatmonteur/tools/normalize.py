"""Capability: ``normalize`` — produce a clean constant-frame-rate intermediate.

Real-world raw footage is variable-frame-rate with messy timestamps. Cutting it
directly desyncs audio. This step rebuilds a clean CFR file that every later step
can safely seek and cut. (Hard-won rule from production use.)

It also brings the audio up to a predictable level by default: the silence
threshold downstream (``cut_silence`` 0.14) is a fraction of PEAK and is only
valid on level-controlled audio — on a quiet recording it shreds words.

That levelling is a plain linear gain, not ``loudnorm``. Loudness is set ONCE,
at the final render (see ``render.py``): running a full loudnorm here as well
put the dialogue through two rounds of dynamic-range compression, which no
studio does — the industry order is "linear gain in the middle, loudness last".
A linear gain moves every sample by the same amount, so the peak-relative cut
threshold gets exactly what it needs while the voice keeps its dynamics.

Pass ``loudness=False`` for flows that must cut RAW audio (e.g. the separate
voice-track branch, where touching the level before the cut destroys the
speech/pause gap — see skills/cutting.md Branch B).
"""

from __future__ import annotations

from ..core.tool import Tool, ToolManifest, ToolResult
from ..core.context import RunContext
from .. import media


# Headroom left below 0 dBFS. The cut threshold only cares that the peak is
# predictable, and a hair of room keeps the intermediate off the ceiling before
# any later filter touches it.
_PEAK_TARGET_DBFS = -1.0
# Below this the move is not worth an extra filter — and re-encoding a file that
# is already at level only adds a rounding error.
_MIN_WORTH_MOVING_DB = 0.5


def _levelling_gain(src: str, *, log) -> float:
    """Linear gain that puts the loudest sample at −1 dBFS, or 0 to leave it alone."""
    peak = media.volume_stats(src).get("max")
    if peak is None:
        log("normalize: no readable audio peak — leaving the level untouched")
        return 0.0
    gain = _PEAK_TARGET_DBFS - peak
    return gain if abs(gain) >= _MIN_WORTH_MOVING_DB else 0.0


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

        gain = _levelling_gain(src, log=ctx.log) if loudness else 0.0
        af = ["-af", f"volume={gain:.1f}dB"] if gain else []
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
            desc=f"normalize → CFR {target_fps}fps{f', gain {gain:+.1f}dB' if gain else ''}",
        )
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"fps": target_fps, "loudness": loudness, "gain_db": gain,
                  "mean_volume_db": media.mean_volume_db(out)},
        )


TOOL = NormalizeTool()
