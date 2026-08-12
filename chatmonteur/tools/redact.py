"""Capability: ``redact`` — permanently cover sensitive screen regions.

The agent inspects the final-cut footage, writes a timecoded plan using
resolution-independent fractions, and runs this tool before any preview leaves
the project.  Solid coverage is deliberate: blur can leave tokens recoverable.
"""

from __future__ import annotations

import json
import pathlib
import re

from .. import media
from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult


_COLOR = re.compile(r"0x[0-9A-Fa-f]{6}\Z")
_DEFAULT_COLOR = "0x0B0B0C"


class RedactTool(Tool):
    manifest = ToolManifest(
        name="redact_ffmpeg",
        capability="redact",
        summary="Permanently cover approved sensitive regions in one ffmpeg pass.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, redactions: str) -> ToolResult:
        media.require("ffmpeg")
        plan_path = pathlib.Path(redactions)
        if not plan_path.is_file():
            raise ToolError(f"redaction plan not found: {plan_path}")
        items = _load_plan(plan_path)
        if not items:
            ctx.log("redact: plan is empty, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"redactions": 0})

        out = ctx.paths.clips / "redacted.mp4"
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        media.run(
            [
                "ffmpeg", "-y", "-i", str(input),
                "-vf", _filter_chain(items),
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                str(out),
            ],
            log=ctx.log,
            desc=f"redact {len(items)} sensitive region(s)",
        )
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"redactions": len(items), "method": "solid"},
        )


def _load_plan(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("redactions", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ToolError("redaction plan must be a list (or {'redactions': [...]})")

    out: list[dict] = []
    for i, raw in enumerate(items):
        number = i + 1
        start, end = float(raw["start"]), float(raw["end"])
        if end <= start:
            raise ToolError(f"redaction #{number}: end must be after start")

        x = float(raw["x"])
        y = float(raw["y"])
        width = float(raw["width"])
        height = float(raw["height"])
        for name, value in (("x", x), ("y", y)):
            if not 0.0 <= value < 1.0:
                raise ToolError(f"redaction #{number}: {name} must be in [0, 1)")
        for name, value in (("width", width), ("height", height)):
            if not 0.0 < value <= 1.0:
                raise ToolError(f"redaction #{number}: {name} must be in (0, 1]")
        if x + width > 1.0 or y + height > 1.0:
            raise ToolError(f"redaction #{number}: box extends outside the frame")

        color = str(raw.get("color", _DEFAULT_COLOR))
        if not _COLOR.fullmatch(color):
            raise ToolError(f"redaction #{number}: color must look like 0x0B0B0C")
        out.append({
            "start": start,
            "end": end,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color.upper().replace("X", "x"),
        })
    return sorted(out, key=lambda item: item["start"])


def _number(value: float) -> str:
    return str(float(value))


def _filter_chain(items: list[dict]) -> str:
    filters = []
    for item in items:
        filters.append(
            "drawbox="
            f"x=iw*{_number(item['x'])}:y=ih*{_number(item['y'])}:"
            f"w=iw*{_number(item['width'])}:h=ih*{_number(item['height'])}:"
            f"color={item['color']}:t=fill:"
            f"enable='between(t,{_number(item['start'])},{_number(item['end'])})'"
        )
    return ",".join(filters)


TOOL = RedactTool()
