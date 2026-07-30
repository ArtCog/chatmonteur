"""Capability: ``storyboard`` — execute the whole phase-③ scene plan in one call.

The storyboard is THE phase-③ artifact (skills/montage.md): the agent reads the
final-cut transcript, plans the visual pass — zooms, B-roll overlays,
meaning-inserts — as ONE document, shows it for approval (the storyboard gate),
and then calls this tool once.

Storyboard (JSON, authored by the agent; every section optional)::

    {
      "zooms":    [ ...see tools/zooms.py... ],
      "overlays": [ ...see tools/overlays.py... ],
      "inserts":  [ ...see tools/inserts.py... ]
    }

The tool executes the sections in the LOAD-BEARING order and chains the video:

1. ``zooms``    — camera geometry locks first;
2. ``overlays`` — placed on the final geometry (a zoom landing after an overlay
   would drag the overlay with it — the classic drift defect);
3. ``inserts``  — the text layer, always on top.

Each section is validated and burned by its own tool; a missing/empty section is
skipped. Color and subtitles stay downstream (phase ④) — graphics burn before
grade only in THIS tool's world because the grade will see the composed frame.
"""

from __future__ import annotations

import json
import pathlib

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from . import inserts as _inserts
from . import overlays as _overlays
from . import zooms as _zooms

# (section, tool, plan-param name) — in the load-bearing execution order.
_SECTIONS = (
    ("zooms", _zooms.TOOL, "zooms"),
    ("overlays", _overlays.TOOL, "overlays"),
    ("inserts", _inserts.TOOL, "inserts"),
)


class StoryboardTool(Tool):
    manifest = ToolManifest(
        name="storyboard_compose",
        capability="storyboard",
        summary="Execute an approved storyboard: zooms -> overlays -> inserts, chained.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, storyboard: str, **section_kwargs) -> ToolResult:
        sb_path = pathlib.Path(storyboard)
        if not sb_path.is_file():
            raise ToolError(
                f"storyboard not found: {sb_path} (the agent writes it after the storyboard gate)"
            )
        data = json.loads(sb_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ToolError("storyboard must be an object with zooms/overlays/inserts sections")
        unknown = set(data) - {s for s, _, _ in _SECTIONS} - {"motion"}
        if unknown:
            raise ToolError(f"storyboard has unknown sections: {sorted(unknown)}")
        _check_one_text_at_a_time(data)

        video = str(input)
        done: list[str] = []
        for section, tool, param in _SECTIONS:
            items = data.get(section) or []
            if not items:
                continue
            plan = ctx.paths.transcripts / f"{section}.json"
            plan.write_text(json.dumps({section: items}, ensure_ascii=False), encoding="utf-8")
            extra = section_kwargs.get(section, {})  # e.g. inserts={"accent": "green"}
            res = tool.run(ctx, input=video, **{param: str(plan)}, **extra)
            video = res.artifacts["video"]
            done.append(f"{section}:{len(items)}")

        if not done:
            ctx.log("storyboard: all sections empty, passing the video through")
        else:
            ctx.log(f"storyboard done ({', '.join(done)})")
        return ToolResult(artifacts={"video": video}, meta={"sections": done})


def _check_one_text_at_a_time(data: dict) -> None:
    """Refuse a plan where two TEXT layers share screen time.

    Артур 2026-07-30: «сейчас на экране был как надпись, так и motion graphic — так не
    должно быть». A meaning-insert and a motion-graphic scene fight for the same attention;
    each must earn its own moment. Declare motion-graphic windows in a ``motion`` section
    (``[{start, end, name}]``) — in VIDEO-LOCAL seconds, the same clock as inserts — and
    this refuses the clash instead of letting the render prove it.
    """
    text_layers = [(s, it) for s in ("inserts", "motion") for it in (data.get(s) or [])]
    for i, (sec_a, a) in enumerate(text_layers):
        for sec_b, b in text_layers[i + 1:]:
            if float(a["start"]) < float(b["end"]) and float(b["start"]) < float(a["end"]):
                raise ToolError(
                    f"two text layers overlap: {sec_a} [{a['start']}–{a['end']}] and "
                    f"{sec_b} [{b['start']}–{b['end']}]. One text at a time — move one, "
                    "or drop it if it doesn't earn its moment."
                )


TOOL = StoryboardTool()
