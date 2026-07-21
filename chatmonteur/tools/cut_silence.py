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

    def run(self, ctx: RunContext, *, input: str, margin: str = "0.15s") -> ToolResult:
        media.require("auto-editor", hint="pip install auto-editor")
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        out = ctx.paths.clips / "cut_silence.mp4"

        media.run(
            [
                "auto-editor", input,
                "--margin", margin,
                "--video-codec", encoder,
                "--video-bitrate", "10M",
                "--no-open",
                "-o", str(out),
            ],
            log=ctx.log,
            desc=f"cut silence (margin {margin}, {encoder})",
        )
        return ToolResult(artifacts={"video": str(out)}, meta={"mean_volume_db": media.mean_volume_db(out)})


TOOL = CutSilenceTool()
