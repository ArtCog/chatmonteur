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
from ..core.errors import MissingDependencyError, ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media
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

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        storyboard: str,
        allow_thin: bool = False,
        **section_kwargs,
    ) -> ToolResult:
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
        _review_plan(data, _duration_of(input), log=ctx.log, allow_thin=allow_thin)

        video = str(input)
        done: list[str] = []
        for section, tool, param in _SECTIONS:
            items = data.get(section) or []
            if not items:
                continue
            plan = ctx.paths.transcripts / f"{section}.json"
            plan.write_text(json.dumps({section: items}, ensure_ascii=False), encoding="utf-8")
            extra = section_kwargs.get(section, {})  # e.g. inserts={"accent": "yellow"}
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


# --- the boringness review ------------------------------------------------------
# Cheap to run on a plan, expensive to discover in a finished render. Every
# threshold is a number from skills/references/engineering-facts.md, not a taste call.
_MAX_DEAD = 90.0        # seconds without a visual event; the pattern-interrupt ceiling
_MAX_TEXT_SHARE = 0.60  # more text-on-screen than this and it reads as animated slides
_MIN_UNIQUE = 0.60      # unique-insert ratio below this = the same card over and over
_MAX_SAME_ZOOM = 2      # a third identical shot size in a row is a rut

# Guo, Kim & Rubin (ACM L@S 2014, 6.9M edX sessions): procedural/screencast video is
# watched 2–3 minutes regardless of its total length — a flat line from a 3-minute
# clip to a 40-minute one, unlike lecture content. So a screencast stretch needs a
# real reset (cut to camera, chapter card, a graphic) on that clock. A zoom is not a
# reset: it is the same screen, closer. Only checked when the agent declares the
# material, since nothing in a plan reveals what the footage actually shows.
_MAX_TUTORIAL_HOLD = 150.0

# Murch's Rule of Six (In the Blink of an Eye): emotion 51%, story 23%, rhythm 10%,
# eye-trace 7%, screen plane 5%, spatial continuity 4%. A move justified only by the
# bottom three is chasing motion — the top three are what an audience feels.
_ZOOM_REASONS = ("emotion", "story", "rhythm", "eye_trace", "plane", "continuity")
_STRONG_REASONS = frozenset(_ZOOM_REASONS[:3])


def _review_plan(data: dict, duration: float | None, log, allow_thin: bool) -> None:
    """Refuse to burn a plan that will read as "he just cut the pauses".

    Артур 2026-07-30: «никакого монтажа я там не заметил — просто субтитры, убрал
    паузы, добавил картинку». That verdict was reachable from the storyboard alone,
    minutes before the render existed. So it gets reached here instead.

    Needs the runtime to judge coverage; without a readable input file the review
    is skipped rather than faked. ``allow_thin=True`` is the conscious override for
    footage that genuinely wants to be left alone.
    """
    if duration is None or duration <= 0:
        return
    # Taste-adjacent, so it advises and never blocks: a weak reason is a prompt to
    # think again, not proof the move is wrong.
    for note in _unjustified_zooms(data):
        log(f"storyboard: {note}")
    findings = _thin_spots(data, duration)
    if not findings:
        return
    if allow_thin:
        for f in findings:
            log(f"storyboard (allowed thin): {f}")
        return
    raise ToolError(
        "storyboard is too thin to read as an edit:\n"
        + "\n".join(f"  • {f}" for f in findings)
        + "\n  Add visual events where they are missing, or pass allow_thin=True if "
        "this footage really should be left plain."
    )


def _unjustified_zooms(data: dict) -> list[str]:
    """Name the moves whose stated reason sits in Murch's bottom three, or is absent."""
    notes = []
    for i, z in enumerate(data.get("zooms") or [], 1):
        reason = str(z.get("reason", "")).strip().lower()
        at = float(z.get("start", z.get("at", 0)) or 0)
        if not reason:
            notes.append(f"zoom #{i} at {at:.0f}s states no reason — if you cannot name "
                         f"one of {', '.join(_ZOOM_REASONS)}, the move is decoration")
        elif reason not in _STRONG_REASONS:
            notes.append(f"zoom #{i} at {at:.0f}s is justified only by '{reason}' — "
                         "following movement is the weakest reason to push in; "
                         "emotion, story or rhythm is what carries a cut")
    return notes


def _thin_spots(data: dict, duration: float) -> list[str]:
    """Pure scoring — the rule set, testable without a media file."""
    findings: list[str] = []
    events = [it for s in ("zooms", "overlays", "inserts", "motion") for it in (data.get(s) or [])]

    if not events:
        return [f"no visual events at all across {duration:.0f}s — this is a raw talking head"]

    start, end = _longest_gap(events, duration)
    if end - start > _MAX_DEAD:
        findings.append(
            f"{end - start:.0f}s with nothing happening ({start:.0f}s–{end:.0f}s); "
            f"attention needs an interrupt at least every {_MAX_DEAD:.0f}s"
        )

    text = [it for s in ("inserts", "motion") for it in (data.get(s) or [])]
    share = _covered(text) / duration
    if share > _MAX_TEXT_SHARE:
        findings.append(
            f"text is on screen {share:.0%} of the time — above {_MAX_TEXT_SHARE:.0%} "
            "it stops being a video and becomes animated slides"
        )

    texts = [str(it.get("text", "")).strip().lower() for it in (data.get("inserts") or [])]
    texts = [t for t in texts if t]
    if len(texts) >= 3 and len(set(texts)) / len(texts) < _MIN_UNIQUE:
        findings.append(
            f"only {len(set(texts))} distinct captions across {len(texts)} inserts — "
            "repeating the same words stops registering"
        )

    if str(data.get("material", "")).strip().lower() == "screencast":
        resets = [it for s in ("overlays", "inserts", "motion") for it in (data.get(s) or [])]
        r_start, r_end = _longest_gap(resets, duration)
        if r_end - r_start > _MAX_TUTORIAL_HOLD:
            findings.append(
                f"{r_end - r_start:.0f}s of screencast with no reset "
                f"({r_start:.0f}s–{r_end:.0f}s) — a tutorial holds attention for about "
                f"{_MAX_TUTORIAL_HOLD / 60:.1f} min before it needs a cut to camera, a "
                "chapter card or a graphic; zooming the same screen does not reset it"
            )

    run = _longest_identical_zoom_run(data.get("zooms") or [])
    if run > _MAX_SAME_ZOOM:
        findings.append(
            f"{run} identical zooms in a row — vary the shot size, a repeated framing "
            "reads as a still"
        )
    return findings


def _longest_gap(events: list[dict], duration: float) -> tuple[float, float]:
    """The widest window with no event, counting the head and the tail.

    The head matters most: dead air before the first visual event is dead air in
    the hook, where retention is decided.
    """
    spans = sorted((float(e["start"]), float(e["end"])) for e in events)
    gaps, cursor = [], 0.0
    for s, e in spans:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < duration:
        gaps.append((cursor, duration))
    return max(gaps, key=lambda g: g[1] - g[0], default=(0.0, 0.0))


def _covered(items: list[dict]) -> float:
    """Total seconds covered by these windows, counting an overlap once."""
    total, cursor = 0.0, float("-inf")
    for s, e in sorted((float(i["start"]), float(i["end"])) for i in items):
        total += max(0.0, e - max(s, cursor))
        cursor = max(cursor, e)
    return total


def _longest_identical_zoom_run(zooms: list[dict]) -> int:
    """How many times in a row the camera lands on the exact same framing."""
    def framing(z: dict) -> tuple:
        return (z.get("kind", "punch"), round(float(z.get("scale", 0) or 0), 2),
                round(float(z.get("cx", 0) or 0), 2), round(float(z.get("cy", 0) or 0), 2))

    best = run = 0
    prev = None
    for z in sorted(zooms, key=lambda z: float(z["start"])):
        run = run + 1 if framing(z) == prev else 1
        prev = framing(z)
        best = max(best, run)
    return best


def _duration_of(video: str) -> float | None:
    """Runtime of the video being decorated, or None if it can't be probed.

    A missing ffprobe is NOT a probe failure — swallowing it here would silently
    switch off the whole boringness gate, which then protects nothing.
    """
    try:
        return float(media.ffprobe_json(video)["format"]["duration"])
    except MissingDependencyError:
        raise
    except (ToolError, KeyError, ValueError, TypeError):
        return None


TOOL = StoryboardTool()
