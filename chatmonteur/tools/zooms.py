"""Capability: ``zooms`` — punch-ins/zooms at emphasis moments (фаза ③).

The DECISION is the AGENT's job (D11): reading the final-cut transcript, it picks
the emphasis moments (skills/motion.md: normal 1.0 / emphasis 1.15 / critical 1.3,
landing ON the anchor word), writes ``zooms.json``, shows the plan, and calls this
tool after approval. The tool executes every zoom in ONE ffmpeg pass.

Zoom plan (JSON, authored by the agent)::

    {"zooms": [
      {"start": 34.2, "end": 37.8, "kind": "punch", "scale": 1.15},
      {"start": 61.0, "end": 66.5, "kind": "push",  "scale": 1.10, "cy": 0.35}
    ]}

Kinds (Артур 2026-07-26: «punch» is the channel standard):

* ``punch`` — instant cut-in, instant cut-out. Reads as a camera-angle change,
  not an effect. THE DEFAULT.
* ``ease``  — smoothstep in/out over ~0.35 s. Soft emphasis.
* ``push``  — slow continuous creep across the window. For a long thought.
* ``drift`` — instant punch, then a slow +3% creep while held. Punch that breathes.

Anti-jitter (learned on real footage): ``zoompan`` recomputes its crop in whole
pixels, so slow moves stutter at 1×. The chain upscales 2× (lanczos) first —
quartering the rounding step — and truncates x/y. Time inside ``zoompan`` is
``in_time`` (NOT ``t`` — that variable simply does not exist there).
"""

from __future__ import annotations

import json
import pathlib

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

_KINDS = {"punch", "ease", "push", "drift"}
# Face-safe zoom centre: a talking-head face sits ABOVE frame centre.
_DEF_CX, _DEF_CY = 0.5, 0.40
_DEF_SCALE = 1.18          # motion.md emphasis tier (Артур 2026-07-30: «можно побольше»)
# Ease ramp. 0.35s read as a snap, not a move — Артур: «зум нужно плавнее». Per-zoom
# override: "ease_seconds". A slow ramp is also where zoompan's quantisation shows, so
# _UPSCALE carries the smoothness (see below).
_EDGE = 0.9
# zoompan crops in WHOLE pixels of its input, so the crop rect jumps 1px at a time and a
# slow zoom stutters. Upscaling first makes that step fractional in output space: at 3×
# a 1px input step = 0.33px out. 2× still stuttered on a 4s ease — verified on frames.
_UPSCALE = 3
_DRIFT_AMP = 0.03          # drift's extra creep on top of the punch


class ZoomsTool(Tool):
    manifest = ToolManifest(
        name="zooms_ffmpeg",
        capability="zooms",
        summary="Execute an approved zoom plan (punch/ease/push/drift) in one ffmpeg pass.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, zooms: str) -> ToolResult:
        media.require("ffmpeg")
        plan_path = pathlib.Path(zooms)
        if not plan_path.is_file():
            raise ToolError(
                f"zoom plan not found: {plan_path} (the agent writes it after plan approval)"
            )
        items = _load_plan(plan_path)
        if not items:
            ctx.log("zooms: plan is empty, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"zooms": 0})

        w, h, fps = _video_meta(input)
        out = ctx.paths.clips / "zoomed.mp4"
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        vf = (
            f"scale=iw*{_UPSCALE}:ih*{_UPSCALE}:flags=lanczos,"
            f"zoompan=z='{_zoom_expr(items)}'"
            # centres are time-gated too (per-zoom cx/cy); outside every window
            # zoom=1 → (iw-iw/zoom)=0, so the centre value there is irrelevant
            f":x='trunc((iw-iw/zoom)*({_centre_expr(items, 'cx')}))'"
            f":y='trunc((ih-ih/zoom)*({_centre_expr(items, 'cy')}))'"
            f":d=1:s={w}x{h}:fps={fps},format=yuv420p"
        )
        media.run(
            [
                "ffmpeg", "-y", "-i", str(input),
                "-vf", vf,
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                str(out),
            ],
            log=ctx.log,
            desc=f"burn {len(items)} zooms ({h}p, {fps}fps)",
        )
        return ToolResult(artifacts={"video": str(out)}, meta={"zooms": len(items)})


def _load_plan(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("zooms", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ToolError("zoom plan must be a list (or {'zooms': [...]})")
    out = []
    for i, it in enumerate(items):
        start, end = float(it["start"]), float(it["end"])
        if end <= start:
            raise ToolError(f"zoom #{i + 1}: end ({end}) must be after start ({start})")
        kind = str(it.get("kind", "punch"))
        if kind not in _KINDS:
            raise ToolError(f"zoom #{i + 1}: unknown kind {kind!r}; choose one of {sorted(_KINDS)}")
        scale = float(it.get("scale", _DEF_SCALE))
        if not 1.0 < scale <= 1.5:
            raise ToolError(f"zoom #{i + 1}: scale {scale} out of the sane range (1.0, 1.5]")
        out.append({
            "start": start, "end": end, "kind": kind, "scale": scale,
            "cx": float(it.get("cx", _DEF_CX)), "cy": float(it.get("cy", _DEF_CY)),
            "edge": float(it.get("ease_seconds", _EDGE)),
        })
    out.sort(key=lambda z: z["start"])
    for a, b in zip(out, out[1:]):
        if b["start"] < a["end"]:
            raise ToolError(
                f"zooms overlap at {b['start']}s — their scales would ADD; separate the windows"
            )
    return out


def _smooth(x: str) -> str:
    """Smoothstep — the move accelerates and settles instead of starting mechanically."""
    return f"({x})*({x})*(3-2*({x}))"


def _envelope(it: dict) -> str:
    """This zoom's contribution to the z expression (0 outside its window)."""
    s, e, amp = it["start"], it["end"], round(it["scale"] - 1, 4)
    gate = f"between(in_time,{s},{e})"
    if it["kind"] == "punch":
        return f"{gate}*{amp}"
    if it["kind"] == "ease":
        edge = it.get("edge", _EDGE)
        rise = f"clip((in_time-{s})/{edge},0,1)"
        fall = f"clip(({e}-in_time)/{edge},0,1)"
        return f"{_smooth(rise)}*{_smooth(fall)}*{amp}"
    ramp = f"clip((in_time-{s})/({e}-{s}),0,1)"
    if it["kind"] == "push":
        return f"{gate}*{ramp}*{amp}"
    # drift: full punch immediately, plus a slow creep on top
    return f"{gate}*({amp}+{_DRIFT_AMP}*{ramp})"


def _zoom_expr(items: list[dict]) -> str:
    return "1+" + "+".join(_envelope(it) for it in items)


def _centre_expr(items: list[dict], axis: str) -> str:
    """Time-gated zoom centre: each window contributes its own cx/cy."""
    base = 0.5
    parts = [str(base)]
    for it in items:
        off = round(it[axis] - base, 4)
        if off:
            parts.append(f"{off}*between(in_time,{it['start']},{it['end']})")
    return "+".join(parts)


def _video_meta(path: str) -> tuple[int, int, float]:
    w, h, fps = 1920, 1080, 30.0
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            w, h = int(s.get("width", 1920)), int(s["height"])
            num, _, den = str(s.get("r_frame_rate", "30/1")).partition("/")
            try:
                fps = round(float(num) / float(den or 1), 3)
            except (ValueError, ZeroDivisionError):
                fps = 30.0
            break
    return w, h, fps


TOOL = ZoomsTool()
