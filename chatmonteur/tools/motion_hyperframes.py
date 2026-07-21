"""Capability: ``motion`` — render motion graphics / animated captions overlay.

Delegates to HyperFrames (HTML/CSS/JS → MP4). The HTML *composition* is authored
by the agent for the specific video; this tool just renders it deterministically
and (optionally) overlays it on the speaker video.

EXPERIMENTAL in v0.1: exercised during dogfooding on real footage, where the
agent writes the composition. Optional pipeline step (``when: motion``).
"""

from __future__ import annotations

from pathlib import Path

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media


class MotionHyperframesTool(Tool):
    manifest = ToolManifest(
        name="motion_hyperframes",
        capability="motion",
        summary="Render a HyperFrames HTML composition to video (motion graphics/captions).",
        backends=("hyperframes",),
        requires_bin=("npx",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, composition: str, name: str = "motion.mp4") -> ToolResult:
        media.require("npx", hint="install Node.js, then `npx hyperframes` is available")
        comp = Path(composition)
        if not comp.exists():
            raise ToolError(f"composition not found: {comp} (the agent should author it first)")
        out = ctx.paths.compositions / name
        media.run(
            ["npx", "--yes", "hyperframes", "render", str(comp), "--output", str(out)],
            log=ctx.log,
            desc=f"render motion ({comp.name})",
        )
        return ToolResult(artifacts={"video": str(out)}, meta={"composition": comp.name})


TOOL = MotionHyperframesTool()
