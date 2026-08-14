"""Capability: ``motion`` — render motion graphics through HyperFrames.

HyperFrames turns an HTML/CSS/JS composition into video. This tool drives it
deterministically and hands back a clip that OUR pipeline composites, which is
the whole point of the design:

**The graphic is rendered WITH ALPHA and overlaid on our own timebase.** The
alternative — letting the composition embed the speaker video and place graphics
against it — puts the graphics on HyperFrames' clock while every burned layer
(zooms, inserts, subtitles) runs on the video's own clock. Two timebases in one
frame is how a caption ends up half a second off its word, and it fails silently.
So: transparent MOV out, `overlays`/`storyboard` in.

Alpha needs ``--format mov`` (ProRes 4444, ``yuva444p12le``). The default ``mp4``
is opaque, and ``--format webm`` gives yuv420p here — also opaque.

Two things that look like tool bugs but are usage errors, both guarded:

* ``hyperframes render`` takes a project **directory**, not an HTML file. A file
  path is accepted here and split into directory + ``--composition``.
* A misspelled variable name renders a blank card rather than failing, so
  ``--strict-variables`` is always on.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

# Alpha-capable output. ProRes 4444 is large but it is an INTERMEDIATE — the
# final encode happens in `render`, and a lossy alpha intermediate would fringe
# every edge against the footage.
_ALPHA_FORMAT = "mov"
_OPAQUE_FORMAT = "mp4"
# HyperFrames publishes frequently. Rendering through an unpinned ``npx hyperframes``
# made yesterday's checked component use today's engine without any repository change.
# Upgrade deliberately: update this pin, run the composition gates, then commit both.
_HYPERFRAMES_PACKAGE = "hyperframes@0.7.109"


class MotionHyperframesTool(Tool):
    manifest = ToolManifest(
        name="motion_hyperframes",
        capability="motion",
        summary="Render a HyperFrames composition to video, with alpha for compositing.",
        backends=("hyperframes",),
        requires_bin=("npx",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        composition: str,
        name: str | None = None,
        variables: dict | None = None,
        alpha: bool = True,
        fps: float | None = None,
        quality: str = "high",
    ) -> ToolResult:
        # Use the RESOLVED path, not the bare name: on Windows npx is `npx.cmd`,
        # and subprocess without a shell only auto-appends `.exe`. Passing "npx"
        # raises a bare FileNotFoundError that reads like Node isn't installed.
        npx = media.require("npx", hint="install Node.js, then `npx hyperframes` is available")
        project, comp_file = _resolve(composition)

        fmt = _ALPHA_FORMAT if alpha else _OPAQUE_FORMAT
        out = ctx.paths.compositions / (name or f"motion.{fmt}")
        # --strict-variables is UNCONDITIONAL: a composition can declare variables the
        # caller forgot to pass, and without the flag that renders a blank card that
        # still writes a file — the out.exists() guard below never notices.
        cmd = [npx, "--yes", _HYPERFRAMES_PACKAGE, "render", str(project),
               "--output", str(out), "--format", fmt, "--quality", quality,
               "--strict-variables"]
        if comp_file:
            cmd += ["--composition", comp_file]
        if fps:
            # Matching the footage matters: a graphic rendered at a different rate
            # judders against it once composited.
            cmd += ["--fps", str(int(fps)) if float(fps).is_integer() else str(fps)]
        if variables:
            # Passed via file, not inline JSON: nested quoting is a reliable way to
            # lose braces to the Windows shell.
            vfile = ctx.paths.compositions / "variables.json"
            vfile.write_text(json.dumps(variables, ensure_ascii=False), encoding="utf-8")
            cmd += ["--variables-file", str(vfile), "--strict-variables"]

        media.run(cmd, log=ctx.log,
                  desc=f"render motion ({comp_file or project.name}, {fmt}{', alpha' if alpha else ''})")
        if not out.exists():
            raise ToolError(f"hyperframes reported success but wrote nothing to {out}")
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"composition": comp_file or project.name, "format": fmt, "alpha": alpha},
        )


def _resolve(composition: str) -> tuple[Path, str | None]:
    """Split what the caller gave us into (project directory, composition file).

    ``hyperframes render`` wants the project directory as its argument; a specific
    HTML file goes through ``--composition`` as a path RELATIVE to that directory.
    Handing it the file directly fails with "Not a directory".
    """
    p = Path(composition)
    if p.is_dir():
        return p, None
    if not p.is_file():
        raise ToolError(f"composition not found: {p} (the agent authors it first)")
    if p.name == "index.html":
        return p.parent, None
    return p.parent, p.name


TOOL = MotionHyperframesTool()
