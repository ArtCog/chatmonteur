"""Capability: ``normalize`` — produce a clean constant-frame-rate intermediate.

Real-world raw footage is variable-frame-rate with messy timestamps. Cutting it
directly desyncs audio. This step rebuilds a clean CFR file that every later step
can safely seek and cut. (Hard-won rule from production use.)

It also brings the audio up to a predictable level by default. auto-editor's
threshold is an ABSOLUTE line — 0.14 of full scale, not of the file's own peak
(measured 2026-08-03: `auto-editor levels` returns 0.768 for a clip and 0.0768
for the same clip 20 dB down, i.e. the numbers scale with the signal instead of
renormalising). So the line only lands in the right place when the recording is
brought to a known level first; on a quiet file every sample sits under 0.14 and
the cutter reads the whole thing as silence.

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
# Same definition of "silent" the file gate uses. A track this quiet is not quiet
# audio, it is the wrong track or a dead microphone — caught on Артур's own OBS
# capture, whose first track is a silent desktop feed at −91 dBFS. Levelling it
# would have computed +90 dB and applied that to the voice track beside it.
_SILENT_DBFS = -60.0


def _levelling_gain(src: str, *, log) -> float:
    """Linear gain that puts the loudest sample at −1 dBFS, or 0 to leave it alone."""
    peak = media.volume_stats(src).get("max")
    if peak is None:
        log("normalize: no readable audio peak — leaving the level untouched")
        return 0.0
    if peak <= _SILENT_DBFS:
        log(f"⚠ normalize: the measured track peaks at {peak} dBFS — that is silence, "
            "not quiet audio. Leaving the level alone; check which OBS track carries "
            "the voice before cutting by level.")
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
