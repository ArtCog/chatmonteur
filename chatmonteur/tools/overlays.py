"""Capability: ``overlays`` — B-roll pictures/clips OVER the talking head (фаза ③).

The channel's b-roll style (skills/motion.md): the speaker STAYS in frame; the
screenshot / image / clip rides on top in the safe zone (upper half / sides —
captions and inserts own the lower center). Not an MTV-cut: an overlay, so the
narration never loses the face.

The DECISION is the AGENT's job (D11): what to show under which words, sourcing
the asset (own capture / Playwright screenshot / CC0 stock), and the storyboard
approval. This tool executes the approved plan in ONE ffmpeg pass.

Overlay plan (JSON, authored by the agent)::

    {"overlays": [
      {"start": 5.5, "end": 9.0, "file": "assets/github.png",
       "pos": "top_right", "width": 0.45}
    ]}

``file`` may be an image (PNG/JPG — looped) or a video (played from its start,
muted). ``width`` is a fraction of the frame width; height keeps aspect.
"""

from __future__ import annotations

import json
import pathlib

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# Safe-zone position presets (x, y as ffmpeg overlay expressions; m = margin px).
# "center" is for evidence cards over a blurred backdrop — everywhere else the
# lower center belongs to captions/inserts and the face must stay visible.
_POSITIONS = {
    "top_right": ("W-w-{m}", "{m}"),
    "top_left": ("{m}", "{m}"),
    "top_center": ("(W-w)/2", "{m}"),
    "center_right": ("W-w-{m}", "(H-h)/2"),
    "center_left": ("{m}", "(H-h)/2"),
    "center": ("(W-w)/2", "(H-h)/2"),
}
_DEF_WIDTH = 0.45      # fraction of frame width
_MARGIN_FRAC = 0.03    # margin from frame edges
_FADE = 0.18           # alpha fade in/out seconds


class OverlaysTool(Tool):
    manifest = ToolManifest(
        name="overlays_ffmpeg",
        capability="overlays",
        summary="Burn approved B-roll overlays (images/clips over the speaker) with ffmpeg.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, overlays: str) -> ToolResult:
        media.require("ffmpeg")
        plan_path = pathlib.Path(overlays)
        if not plan_path.is_file():
            raise ToolError(
                f"overlay plan not found: {plan_path} (the agent writes it after storyboard approval)"
            )
        items = _load_plan(plan_path)
        if not items:
            ctx.log("overlays: plan is empty, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"overlays": 0})

        w, h = _video_wh(input)
        out = ctx.paths.clips / "overlaid.mp4"
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        cmd = ["ffmpeg", "-y", "-i", str(input)]
        for it in items:
            dur = f"{it['end'] - it['start']:.3f}"
            if it["is_image"]:
                cmd += ["-loop", "1", "-t", dur, "-i", it["file"]]
            else:
                cmd += ["-t", dur, "-an", "-i", it["file"]]  # b-roll clips are muted
        cmd += ["-filter_complex", _filter_graph(items, w, h),
                "-map", "[v]", "-map", "0:a?",
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
        media.run(cmd, log=ctx.log, desc=f"burn {len(items)} overlays ({h}p)")
        return ToolResult(artifacts={"video": str(out)}, meta={"overlays": len(items)})


def _load_plan(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("overlays", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ToolError("overlay plan must be a list (or {'overlays': [...]})")
    out = []
    for i, it in enumerate(items):
        f = pathlib.Path(str(it.get("file", "")))
        if not f.is_file():
            raise ToolError(f"overlay #{i + 1}: file not found: {f}")
        start, end = float(it["start"]), float(it["end"])
        if end <= start:
            raise ToolError(f"overlay #{i + 1}: end ({end}) must be after start ({start})")
        pos = str(it.get("pos", "top_right"))
        if pos not in _POSITIONS:
            raise ToolError(f"overlay #{i + 1}: unknown pos {pos!r}; choose one of {sorted(_POSITIONS)}")
        width = float(it.get("width", _DEF_WIDTH))
        if not 0.1 <= width <= 0.7:
            raise ToolError(f"overlay #{i + 1}: width {width} outside sane range [0.1, 0.7] "
                            "(bigger would bury the speaker — cut away instead)")
        backdrop = it.get("backdrop")
        if backdrop not in (None, "blur"):
            raise ToolError(f"overlay #{i + 1}: unknown backdrop {backdrop!r}; only 'blur'")
        out.append({
            "file": str(f), "start": start, "end": end, "pos": pos, "width": width,
            "is_image": f.suffix.lower() in _IMAGE_EXT, "backdrop": backdrop,
        })
    return out


def _video_wh(path: str) -> tuple[int, int]:
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            return int(s.get("width", 1920)), int(s["height"])
    return 1920, 1080


def _filter_graph(items: list[dict], width: int, height: int) -> str:
    m = round(_MARGIN_FRAC * width)
    parts = []
    prev = "0:v"
    for i, it in enumerate(items):
        dur = it["end"] - it["start"]
        # On a short window the full fades would overlap and the asset never
        # reaches opacity — scale them down so in+out always fit inside.
        fade = min(_FADE, dur / 2.5)
        target_w = round(width * it["width"] / 2) * 2  # encoder needs even dims
        xe, ye = _POSITIONS[it["pos"]]
        x, y = xe.format(m=m), ye.format(m=m)
        if it.get("backdrop") == "blur":
            # The motion floor holds while the viewer reads: the card sits on a
            # blurred copy of the LIVE frame, never a flat colour (skills/motion.md).
            parts.append(f"[{prev}]split[base{i}][tob{i}]")
            parts.append(f"[tob{i}]boxblur=20:2[bl{i}]")
            parts.append(
                f"[base{i}][bl{i}]overlay=0:0:"
                f"enable='between(t,{it['start']:.3f},{it['end']:.3f})'[bg{i}]"
            )
            prev = f"bg{i}"
        parts.append(
            f"[{i + 1}:v]scale={target_w}:-2,format=rgba,"
            f"fade=in:st=0:d={fade:.3f}:alpha=1,"
            f"fade=out:st={max(0.0, dur - fade - 0.04):.3f}:d={fade:.3f}:alpha=1,"
            f"setpts=PTS+{it['start']:.3f}/TB[o{i}]"
        )
        parts.append(
            f"[{prev}][o{i}]overlay={x}:{y}:"
            f"enable='between(t,{it['start']:.3f},{it['end']:.3f})'[v{i + 1}]"
        )
        prev = f"v{i + 1}"
    parts.append(f"[{prev}]format=yuv420p[v]")
    return ";".join(parts)


TOOL = OverlaysTool()
