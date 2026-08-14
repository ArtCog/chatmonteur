"""Capability: ``color`` — apply a 3D LUT (.cube) for a graded look.

Thin wrapper over ffmpeg's ``lut3d``. LUTs ship in ``presets/luts/`` and are
referenced by name (``warm_film``) or absolute path.
"""

from __future__ import annotations

from pathlib import Path

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

_PACKAGED_LUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "presets" / "luts"
_SOURCE_LUT_DIR = Path(__file__).resolve().parents[2] / "presets" / "luts"
_LUT_DIR = _PACKAGED_LUT_DIR if _PACKAGED_LUT_DIR.is_dir() else _SOURCE_LUT_DIR


class ColorTool(Tool):
    manifest = ToolManifest(
        name="color_lut3d_ffmpeg",
        capability="color",
        summary="Apply a .cube 3D LUT via ffmpeg lut3d.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, lut: str | None = None) -> ToolResult:
        if not lut or lut == "none":
            # Default = the original look, ungraded (Артур 2026-07-24). Grading is
            # an explicit choice the agent ASKS about, never a silent default.
            ctx.log("color: no LUT chosen, passing through ungraded")
            return ToolResult(artifacts={"video": str(input)}, meta={"lut": None})
        media.require("ffmpeg")
        lut_path = self._resolve_lut(lut)
        # The filename goes INTO a filtergraph, where , : ; ' [ ] = are syntax.
        # Escaping every variant is fragile; renaming a LUT file is trivial.
        if any(ch in lut_path.name for ch in ",;:'[]="):
            raise ToolError(
                f"LUT filename {lut_path.name!r} contains filtergraph syntax "
                "characters — rename the file (letters, digits, - _ . are safe)"
            )
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        out = ctx.paths.clips / "graded.mp4"
        # Run from the LUT's folder, reference by bare name (dodge drive colon).
        media.run(
            [
                "ffmpeg", "-y", "-i", str(input),
                # lut3d works in RGB and emits gbrp — convert back to yuv420p so
                # downstream stays standard and playable.
                "-vf", f"lut3d={lut_path.name},format=yuv420p",
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                str(out),
            ],
            log=ctx.log,
            desc=f"color grade ({lut_path.stem})",
            cwd=lut_path.parent,
        )
        return ToolResult(artifacts={"video": str(out)}, meta={"lut": lut_path.stem})

    def _resolve_lut(self, lut: str) -> Path:
        p = Path(lut)
        if p.is_file():
            return p
        candidate = _LUT_DIR / (lut if lut.endswith(".cube") else f"{lut}.cube")
        if candidate.is_file():
            return candidate
        available = ", ".join(sorted(f.stem for f in _LUT_DIR.glob("*.cube"))) or "(none)"
        raise ToolError(f"LUT '{lut}' not found. Available: {available}")


TOOL = ColorTool()
