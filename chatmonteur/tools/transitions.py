"""Capability: ``transitions`` — join clips with a deliberate seam.

The tool that assembles a timeline out of separate pieces: a title card in front
of the body, several takes, intro → body → outro. Until now that was done by hand
with a raw ffmpeg line, which is exactly where the timebase mistakes live.

Three kinds, not forty. A transition is punctuation, and a video that uses a
different one at every join reads as a demo of the software rather than an edit:

* ``cut``       — no seam. The default, and the right answer most of the time.
* ``crossfade`` — one picture dissolves into the next. Change of subject.
* ``fade``      — through black. Change of chapter: intro → body, body → outro.

Discipline is enforced, not suggested: one kind must own at least 60 % of the
joins (``_MIN_PRIMARY``). See ``_check_discipline``.

Plan (JSON, authored by the agent)::

    {"clips": ["title.mov", "body.mp4", "outro.mp4"],
     "joins": [{"kind": "fade"}, {"kind": "cut"}]}

``joins`` has one entry per gap between clips; a missing entry is a hard cut.
``duration`` defaults to a value scaled by total runtime — a 40-second short wants
a 0.4 s dissolve, a 20-minute talk wants 1.2 s. ``audio_duration`` may be set
longer than the picture's to let sound arrive before the image, which is the
cheapest way to make a seam feel intentional.

On J/L cuts: our usual case gets them for free. A full-frame cutaway is burned by
``overlays``, which never touches ``0:a`` — the narration runs straight through
while the picture changes. That IS an L-cut. This tool only needs to handle the
rarer case of joining pieces that carry their own separate sound.

The canvas (resolution and fps) comes from the LONGEST clip: the body footage
defines the video, and a 2-second title card adapts to it rather than the reverse.
"""

from __future__ import annotations

import json
import pathlib

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

_KINDS = ("cut", "crossfade", "fade")
# ffmpeg xfade names for the two soft kinds. `cut` never reaches xfade.
_XFADE = {"crossfade": "fade", "fade": "fadeblack"}
# Transition length scales with the runtime it lives in: (runtime ceiling, seconds).
_BY_RUNTIME = ((60.0, 0.4), (600.0, 0.75), (float("inf"), 1.2))
_MIN_PRIMARY = 0.60      # one kind must own this share of the joins
_MIN_JOINS_TO_JUDGE = 3
_MAX_CLIP_SHARE = 0.5    # a transition may not eat more than half the shorter clip


class TransitionsTool(Tool):
    manifest = ToolManifest(
        name="transitions_ffmpeg",
        capability="transitions",
        summary="Join clips with cut / crossfade / fade-through-black in one pass.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        plan: str | None = None,
        clips: list[str] | None = None,
        joins: list[dict] | None = None,
        name: str = "joined.mp4",
        allow_scattered: bool = False,
    ) -> ToolResult:
        media.require("ffmpeg")
        spec = _load_plan(plan) if plan else {}
        paths = [str(c) for c in (spec.get("clips") or clips or [])]
        if len(paths) < 2:
            raise ToolError("transitions needs at least two clips to join")
        for p in paths:
            if not pathlib.Path(p).is_file():
                raise ToolError(f"clip not found: {p}")

        info = [_probe(p) for p in paths]
        runtime = sum(i["duration"] for i in info)
        plan_joins = _normalise_joins(spec.get("joins") or joins or [], len(paths) - 1, runtime)
        _check_discipline(plan_joins, log=ctx.log, allow_scattered=allow_scattered)
        _check_room(info, plan_joins)

        canvas = max(info, key=lambda i: i["duration"])
        w, h, fps = canvas["width"], canvas["height"], canvas["fps"]
        real_joins = _effective(plan_joins, fps)
        graph, silent = _graph(info, real_joins, w, h, fps)

        cmd = ["ffmpeg", "-y"]
        for i in info:
            cmd += ["-i", i["file"]]
        for idx in silent:  # a clip with no sound of its own needs a real silent track
            cmd += ["-f", "lavfi", "-t", f"{info[idx]['duration']:.3f}",
                    "-i", "anullsrc=r=48000:cl=stereo"]

        encoder = media.detect_encoder(ctx.config.encode.encoder)
        out = ctx.paths.clips / name
        cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                str(out)]
        kinds = ", ".join(f"{j['kind']}" for j in plan_joins)
        media.run(cmd, log=ctx.log, desc=f"join {len(paths)} clips at {w}x{h}@{fps} ({kinds})")
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"clips": len(paths), "joins": [j["kind"] for j in plan_joins],
                  "expected_duration": round(_total(info, real_joins), 3)},
        )


# --- planning (pure) ------------------------------------------------------------

def _default_duration(runtime: float) -> float:
    """How long a transition should be inside a video of this length."""
    return next(secs for ceiling, secs in _BY_RUNTIME if runtime <= ceiling)


def _normalise_joins(raw: list[dict], count: int, runtime: float) -> list[dict]:
    """One entry per gap, defaults filled in. Missing entries are hard cuts."""
    default = _default_duration(runtime)
    out: list[dict] = []
    for i in range(count):
        item = raw[i] if i < len(raw) else {}
        kind = str(item.get("kind", "cut"))
        if kind not in _KINDS:
            raise ToolError(f"join #{i + 1}: unknown kind {kind!r}; choose one of {list(_KINDS)}")
        d = 0.0 if kind == "cut" else float(item.get("duration", default))
        if kind != "cut" and not 0.1 <= d <= 3.0:
            raise ToolError(f"join #{i + 1}: duration {d}s outside the sane range [0.1, 3.0]")
        out.append({
            "kind": kind,
            "duration": d,
            # sound may lead the picture: a longer audio blend starts earlier than
            # the visual one, which is what makes a seam feel deliberate
            "audio_duration": float(item.get("audio_duration", d)) if kind != "cut" else 0.0,
        })
    return out


def _check_discipline(joins: list[dict], log, allow_scattered: bool) -> None:
    """Refuse a timeline that changes its punctuation at every sentence.

    A different transition at every join is the single loudest amateur tell in
    assembly. One kind carries the video; the others are accents.
    """
    if len(joins) < _MIN_JOINS_TO_JUDGE:
        return
    kinds = [j["kind"] for j in joins]
    primary = max(set(kinds), key=kinds.count)
    share = kinds.count(primary) / len(kinds)
    if share >= _MIN_PRIMARY:
        return
    msg = (f"transitions are scattered: no kind covers {_MIN_PRIMARY:.0%} of the joins "
           f"(best is '{primary}' at {share:.0%} of {len(kinds)}). Pick one primary "
           "transition and keep the rest as rare accents.")
    if allow_scattered:
        log(f"transitions (allowed): {msg}")
        return
    raise ToolError(msg)


def _check_room(info: list[dict], joins: list[dict]) -> None:
    """A transition may not eat more than half of the shorter clip it joins.

    Fitting is not the same as working: xfade produces garbage once the offset
    lands past the end of a stream, and well before that a dissolve consuming
    most of a shot means the shot was never really on screen.
    """
    for i, j in enumerate(joins):
        d = max(j["duration"], j["audio_duration"])
        if d <= 0:
            continue
        shortest = min(info[i]["duration"], info[i + 1]["duration"])
        if d > shortest * _MAX_CLIP_SHARE:
            raise ToolError(
                f"join #{i + 1}: a {d}s transition is too much for clips of "
                f"{info[i]['duration']:.1f}s and {info[i + 1]['duration']:.1f}s — "
                f"keep it under {shortest * _MAX_CLIP_SHARE:.1f}s so the shorter shot "
                "still gets seen"
            )


def _effective(joins: list[dict], fps: float) -> list[dict]:
    """Joins as the filter graph will really run them.

    Inside a blended chain a hard cut becomes a one-frame dissolve — a uniform
    chain is worth the single frame it costs, and one frame of blend is invisible
    (the same trick that hides a jump cut). All-cut timelines are left exact and
    go through ``concat`` instead.
    """
    if all(j["kind"] == "cut" for j in joins):
        return joins
    return [{**j, "duration": j["duration"] or 1.0 / fps} for j in joins]


def _offsets(durations: list[float], joins: list[dict]) -> list[float]:
    """Where each xfade starts on the timeline built SO FAR.

    Every transition overlaps its two clips, so the composed stream is shorter
    than the sum of its parts — offset i is measured against the length after
    i-1 joins, never against the raw total. Getting this wrong drifts a little
    more at every seam, which is how a join at minute nine ends up seconds off.
    """
    out: list[float] = []
    composed = durations[0]
    for i, j in enumerate(joins):
        d = j["duration"]
        out.append(round(composed - d, 4))
        composed += durations[i + 1] - d
    return out


def _total(info: list[dict], joins: list[dict]) -> float:
    return sum(i["duration"] for i in info) - sum(j["duration"] for j in joins)


# --- the filter graph -----------------------------------------------------------

def _graph(info: list[dict], joins: list[dict], w: int, h: int, fps: float) -> tuple[str, list[int]]:
    """Build the filter graph; also report which clips need a synthetic silent track.

    ``joins`` must already have been through ``_effective``.
    """
    parts: list[str] = []
    silent = [i for i, c in enumerate(info) if not c["has_audio"]]
    frame = 1.0 / fps

    for i, c in enumerate(info):
        parts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}]"
        )
        src = f"{len(info) + silent.index(i)}:a" if i in silent else f"{i}:a"
        parts.append(f"[{src}]aresample=48000,asetpts=N/SR/TB[a{i}]")

    if all(j["kind"] == "cut" for j in joins):
        # Nothing to blend: concat is exact, with no frame spent on a seam.
        streams = "".join(f"[v{i}][a{i}]" for i in range(len(info)))
        parts.append(f"{streams}concat=n={len(info)}:v=1:a=1[v][a]")
        return ";".join(parts), silent

    offsets = _offsets([c["duration"] for c in info], joins)
    vprev, aprev = "v0", "a0"
    for i, j in enumerate(joins):
        transition = _XFADE.get(j["kind"], "fade")
        parts.append(
            f"[{vprev}][v{i + 1}]xfade=transition={transition}:"
            f"duration={j['duration']:.4f}:offset={offsets[i]:.4f}[vx{i}]"
        )
        parts.append(
            f"[{aprev}][a{i + 1}]acrossfade="
            f"d={max(j['audio_duration'], frame):.4f}:c1=tri:c2=tri[ax{i}]"
        )
        vprev, aprev = f"vx{i}", f"ax{i}"
    parts.append(f"[{vprev}]format=yuv420p[v]")
    parts.append(f"[{aprev}]anull[a]")
    return ";".join(parts), silent


def _probe(path: str) -> dict:
    info = media.ffprobe_json(path)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ToolError(f"clip has no video stream: {path}")
    return {
        "file": path,
        "duration": float(info.get("format", {}).get("duration") or 0.0),
        "width": int(video.get("width") or 1920),
        "height": int(video.get("height") or 1080),
        "fps": media.source_fps(path),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def _load_plan(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.is_file():
        raise ToolError(f"transitions plan not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ToolError("transitions plan must be an object with 'clips' and 'joins'")
    return data


TOOL = TransitionsTool()
