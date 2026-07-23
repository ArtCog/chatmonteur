"""Capability: ``cut_silence`` — remove dead air with auto-editor.

auto-editor is the proven tool for silence removal; we let it render directly
(parsing its output and re-cutting was tested and produced artifacts). Runs
per clip — keep inputs short (auto-editor is O(n^2) on long files).
"""

from __future__ import annotations

from ..core.context import RunContext
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media


class CutSilenceTool(Tool):
    manifest = ToolManifest(
        name="cut_silence_auto_editor",
        capability="cut_silence",
        summary="Remove silences/dead-air via auto-editor (renders directly).",
        backends=("auto-editor",),
        requires_bin=("auto-editor", "ffmpeg"),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        threshold: float = 0.14,
        stream: int | None = None,
        margin: str = "0.12s,0.10s",
    ) -> ToolResult:
        """Remove dead air with auto-editor.

        ``threshold`` is a fraction of the track's peak, so it is only meaningful
        on level-controlled audio. Two proven presets from production:
          * Branch A — single mixed track, normalised to −14 LUFS first: ``0.14``.
          * Branch B — separate clean voice track (OBS mic on stream 1), RAW: pass
            ``threshold=0.06, stream=1`` and DON'T normalise first.
        ``--margin`` lead 0.12s protects soft word onsets, tail 0.10s kills breath.
        ``--sample-rate 48000`` stops auto-editor upsampling to 96k (clicks at joins).
        """
        media.require("auto-editor", hint="pip install auto-editor")
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        out = ctx.paths.clips / "cut_silence.mp4"

        edit = f"audio:threshold={threshold}"
        if stream is not None:
            edit = f"audio:threshold={threshold},stream={stream}"

        media.run(
            [
                "auto-editor", input,
                "--edit", edit,
                "--margin", margin,
                "--video-codec", encoder,
                "--video-bitrate", "10M",
                "--audio-bitrate", "256k",
                "--sample-rate", "48000",
                "--no-open",
                "-o", str(out),
            ],
            log=ctx.log,
            desc=f"cut silence (edit {edit}, margin {margin}, {encoder})",
        )
        return ToolResult(artifacts={"video": str(out)}, meta={"mean_volume_db": media.mean_volume_db(out)})


TOOL = CutSilenceTool()
