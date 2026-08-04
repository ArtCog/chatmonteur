"""Capability: ``cues`` — burn the brand's cue list onto the video (фаза ③).

The cue list is the brandbook's own hand-off format (``brand-manifest.json`` →
``cueFormat``): a time-sorted list of «show element X at second T with this text».
The agent authors it from the final-cut transcript; this tool checks it against
the brand's rules, renders each cue's component, and composites them in one pass.

Cue list (JSON, authored by the agent)::

    {"cues": [
      {"t": 12.4, "element": "03", "text": ["Джулиан Иванов", "AI Automation · автор"]},
      {"t": 84.2, "element": "B", "text": "это абсолютно бесплатно",
       "highlightWord": "бесплатно", "holdSec": 2},
      {"t": 141.0, "element": "N", "vars": {"line1": "…", "line2": "…"}}
    ]}

**The gate is the point.** A brandbook that only lives in prose gets violated by
the fourth video: too many accent plates, two graphics on screen at once, three
different transitions in one film. Those rules are numbers in the manifest, so
they are checked here rather than trusted. ``dry_run=True`` runs every check and
renders nothing — that is the cheap way to hold the gate before approval.

Text mapping is deliberately dumb. ``vars`` is the real interface and is checked
against the component's declared variables; ``text`` is sugar that only works
when it is unambiguous (one string for a one-variable component, or an array
whose length matches). Anything else fails loudly WITH the variable names rather
than guessing — a wrong guess renders a plausible card that says the wrong thing,
which is the one failure nobody catches before YouTube.

Everything renders WITH ALPHA, including the full-frame cards: an opaque
composition simply carries an opaque background through, and the uniform path
keeps a card's own fade-in from being flattened into a hard cut.
"""

from __future__ import annotations

import json
import math
import pathlib

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media
from . import motion_hyperframes as _motion

_BRAND = pathlib.Path(__file__).resolve().parents[2] / "assets" / "brand" / "default"
_CATALOG = _BRAND / "catalog.json"
_MANIFEST = _BRAND / "brand-manifest.json"

# Accent overlays that shout. The manifest caps these separately from the rest:
# «A и E — на два сильнейших момента», and a film that shouts throughout shouts
# about nothing.
_LOUD = {"A", "E"}


class CuesTool(Tool):
    manifest = ToolManifest(
        name="cues_hyperframes",
        capability="cues",
        summary="Check a brand cue list against the manifest's budgets and burn it in.",
        backends=("hyperframes", "ffmpeg"),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        cues: str,
        allow_thin: bool = False,
        dry_run: bool = False,
    ) -> ToolResult:
        catalog, manifest = _load_brand()
        plan = _resolve(_load_cues(pathlib.Path(cues)), catalog)
        _check(plan, manifest, duration=_duration_of(input), log=ctx.log, allow_thin=allow_thin)

        if dry_run:
            ctx.log(f"cues: {len(plan)} cues pass the brand gate (dry run, nothing rendered)")
            return ToolResult(meta={"cues": len(plan), "dry_run": True})
        if not plan:
            ctx.log("cues: list is empty, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"cues": 0})

        media.require("ffmpeg")
        for i, cue in enumerate(plan):
            res = _motion.TOOL.run(
                ctx,
                composition=str(_BRAND / cue["component"] / "index.html"),
                name=f"cue_{i + 1:02d}_{cue['component_name']}.mov",
                variables=cue["vars"] or None,
                alpha=True,
                fps=media.source_fps(input),
            )
            cue["file"] = res.artifacts["video"]

        out = ctx.paths.clips / "cued.mp4"
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        cmd = ["ffmpeg", "-y", "-i", str(input)]
        for cue in plan:
            cmd += ["-an", "-i", cue["file"]]
        cmd += ["-filter_complex", _filter_graph(plan),
                "-map", "[v]", "-map", "0:a?",
                "-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
        media.run(cmd, log=ctx.log, desc=f"burn {len(plan)} brand cues")
        return ToolResult(artifacts={"video": str(out)},
                          meta={"cues": len(plan),
                                "elements": [c["element"] for c in plan]})


# --- loading -------------------------------------------------------------------

def _load_brand() -> tuple[dict, dict]:
    for path in (_CATALOG, _MANIFEST):
        if not path.is_file():
            raise ToolError(f"brand file missing: {path} (run assets/brand/default/build_catalog.py)")
    return (json.loads(_CATALOG.read_text(encoding="utf-8")),
            json.loads(_MANIFEST.read_text(encoding="utf-8")))


def _load_cues(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        raise ToolError(f"cue list not found: {path} (the agent writes it after the storyboard gate)")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("cues", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ToolError("cue list must be a list (or {'cues': [...]})")
    return items


# --- resolving a cue to a renderable composition -------------------------------

def _resolve(items: list[dict], catalog: dict) -> list[dict]:
    # The catalog keys cards by their printed id («02·B», «07·A»); cue lists write
    # them the way a keyboard does («02B»), which is also how the manifest's own
    # element lists spell them.
    by_id = {c["id"].replace("·", ""): c for c in catalog["cards"]}
    not_drawn = {entry.split()[0] for entry in catalog.get("notDrawn", [])}
    plan = []
    for n, raw in enumerate(items, 1):
        where = f"cue #{n}"
        if not isinstance(raw, dict):
            raise ToolError(f"{where}: must be an object")
        element = str(raw.get("element", "")).replace("·", "")
        if element in not_drawn:
            # The manifest promises these; the designer never drew them. Saying so
            # beats «unknown element» — the agent read the name in the manifest and
            # is right to expect it to exist.
            raise ToolError(f"{where}: element {element} is named by the manifest but the "
                            "designer never drew a card for it. Nothing renders it yet — "
                            "wait for the card rather than inventing one.")
        card = by_id.get(element)
        if card is None:
            raise ToolError(f"{where}: unknown element {element!r}; "
                            f"see assets/brand/default/catalog.json")
        if card["status"] != "ready":
            raise ToolError(f"{where}: element {element} is '{card['status']}' — "
                            f"{card.get('routeNote') or card['name']}. Nothing renders it yet.")

        t = float(raw.get("t", -1))
        if t < 0:
            raise ToolError(f"{where}: 't' must be a second in the video, got {raw.get('t')!r}")
        hold = raw.get("holdSec")
        hold = float(hold) if hold is not None else float(card["durationSec"])
        if hold <= 0:
            raise ToolError(f"{where}: holdSec must be positive, got {hold}")

        position = raw.get("position")
        if position not in (None, "center", "left", "right"):
            raise ToolError(f"{where}: unknown position {position!r}; "
                            "choose center | left | right")

        variables = _variables(raw, card, where)
        plan.append({
            "element": element,
            "kind": card["kind"],
            "component": card["component"],
            "component_name": card["component"].rsplit("/", 1)[-1],
            "start": t,
            "end": t + hold,
            "vars": variables,
            "position": position,
            # computed here, where the card is in hand; the gate only compares
            "floorSec": _reading_floor(card, variables),
        })
    plan.sort(key=lambda c: c["start"])
    return plan


def _variables(raw: dict, card: dict, where: str) -> dict:
    declared = [v["id"] for v in card["variables"]]
    out = dict(raw.get("vars") or {})
    unknown = [k for k in out if k not in declared]
    if unknown:
        raise ToolError(f"{where}: element {card['id']} has no variable(s) {unknown}; "
                        f"it declares {declared}")

    text = raw.get("text")
    word = raw.get("highlightWord")
    if word is not None:
        # The manifest's own example for accent B. Only a component that declares
        # the three-part split can express it — anywhere else the word would be
        # silently dropped, and the plate would read as a plain line.
        if not {"pre", "word", "post"} <= set(declared):
            raise ToolError(f"{where}: 'highlightWord' needs an element that splits a line "
                            f"around it (pre/word/post); {card['id']} declares {declared}")
        if not isinstance(text, str) or word not in text:
            raise ToolError(f"{where}: 'highlightWord' {word!r} must appear inside 'text'")
        pre, _, post = text.partition(word)
        out.setdefault("pre", pre.strip())
        out.setdefault("word", word)
        out.setdefault("post", post.strip())
        text = None

    if text is not None:
        free = [d for d in declared if d not in out]
        values = [text] if isinstance(text, str) else [str(v) for v in text]
        if len(values) != len(free):
            raise ToolError(
                f"{where}: 'text' has {len(values)} line(s) but {card['id']} needs "
                f"{len(free)} value(s) for {free}. Use 'vars' to say which is which — "
                "guessing here is how a card ships the right words in the wrong slots.")
        out.update(dict(zip(free, values)))

    meta = raw.get("meta")
    if meta:
        unknown = [k for k in meta if k not in declared]
        if unknown:
            raise ToolError(f"{where}: 'meta' key(s) {unknown} are not variables of "
                            f"{card['id']}; it declares {declared}")
        out.update({k: str(v) for k, v in meta.items()})
    return out


# --- the gate ------------------------------------------------------------------

# Extra reading time per word, from the UK CAP/BCAP broadcast guidance ("On screen
# text and subtitling in TV ads", 2016): 0.2 s per word, 0.25 s once the block runs
# over three lines. Subtitle CPS does NOT apply — a subtitle times words the viewer
# is also hearing, a card is read cold.
#
# The guidance's fixed 2–3 s "recognition period" is deliberately NOT added on top:
# the designer's own durationSec already covers noticing the card (it animates in),
# and measured against 57 drawn cards the raw formula contradicted 19 of them. The
# card as drawn IS the brand's answer; CAP/BCAP only prices the words the agent adds
# beyond it.
_READ_SEC_PER_WORD = 0.2
_READ_SEC_PER_WORD_DENSE = 0.25
_DENSE_LINES = 3


def _word_count(values) -> tuple[int, int]:
    lines = [str(v) for v in values if str(v).strip()]
    return sum(len(line.split()) for line in lines), len(lines)


def _reading_floor(card: dict, variables: dict) -> float:
    """Shortest honest hold for this cue: the drawn duration, plus time for extra text.

    Two defects this refuses: cutting a card shorter than the animation the designer
    drew, and pouring a paragraph into a card drawn for a phrase without paying the
    reading time for it.
    """
    drawn = float(card["durationSec"])
    written, lines = _word_count(variables.values())
    designed, _ = _word_count(v.get("default", "") for v in card["variables"])
    extra = max(0, written - designed)
    if not extra:
        return drawn
    rate = _READ_SEC_PER_WORD_DENSE if lines > _DENSE_LINES else _READ_SEC_PER_WORD
    return drawn + extra * rate

def _check(plan: list[dict], manifest: dict, *, duration: float | None,
           log, allow_thin: bool) -> None:
    budget = manifest["accentOverlays"]["budget"]
    motion = manifest["motion"]

    # Nothing shares screen time. The manifest says onScreenSimultaneously: 1, and
    # this is the rule a plan breaks by accident — two cues authored from different
    # sentences that happen to overlap by a second.
    if int(budget.get("onScreenSimultaneously", 1)) == 1:
        for a, b in zip(plan, plan[1:]):
            if b["start"] < a["end"]:
                raise ToolError(
                    f"element {a['element']} (until {a['end']:.1f}s) and {b['element']} "
                    f"(from {b['start']:.1f}s) share the screen; the brand allows one at a time")

    paragraph_max = float(motion["holdSec"]["paragraphMax"])
    for cue in plan:
        held = cue["end"] - cue["start"]
        if held > paragraph_max:
            raise ToolError(f"element {cue['element']} at {cue['start']:.1f}s holds "
                            f"{held:.1f}s; the manifest's ceiling is {paragraph_max}s")
        floor = cue.get("floorSec", 0.0)
        if held + 1e-6 < floor:
            raise ToolError(
                f"element {cue['element']} at {cue['start']:.1f}s holds {held:.1f}s, "
                f"but needs {floor:.1f}s — the card was drawn to run that long, and "
                "text nobody has time to read was never really on screen.")

    # One transition for the whole film, not a sampler.
    used = {c["element"] for c in plan if c["element"] in _transition_ids(manifest)}
    if len(used) > 1:
        raise ToolError(f"the film uses {len(used)} kinds of transition ({sorted(used)}); "
                        "the brand allows one per video")

    accents = [c for c in plan if c["kind"] == "accent"]
    loud = [c for c in accents if c["element"] in _LOUD]
    if len(loud) > int(budget["maxLoudHooks"]):
        raise ToolError(f"{len(loud)} loud accents ({sorted(c['element'] for c in loud)}); "
                        f"the brand allows {budget['maxLoudHooks']} — they are for the "
                        "strongest moments, and a film that shouts throughout shouts about nothing")

    gap = float(budget["minGapSec"])
    for a, b in zip(accents, accents[1:]):
        if b["start"] - a["start"] < gap:
            raise ToolError(f"accents {a['element']} and {b['element']} are "
                            f"{b['start'] - a['start']:.1f}s apart; the brand wants {gap:.0f}s")

    if duration:
        # The manifest states a RATE (5–8 per 10 min), but a rate measured over a
        # 30-second clip is noise: one accent extrapolates to twenty. So it becomes a
        # count for THIS runtime, and the ceiling never drops below one full budget —
        # a short film is allowed to be as dense as a long one, just not denser.
        tenths = duration / 600.0
        lo, hi = float(budget["per10min"]["min"]), float(budget["per10min"]["max"])
        ceiling = max(hi, math.ceil(hi * tenths))
        floor = math.floor(lo * tenths)
        if len(accents) > ceiling:
            raise ToolError(f"{len(accents)} accents in {duration / 60:.1f} min; the brand's "
                            f"ceiling for a film this long is {ceiling:.0f} "
                            f"({hi:.0f} per 10 min)")
        if len(accents) < floor:
            msg = (f"only {len(accents)} accents in {duration / 60:.1f} min; the brand wants "
                   f"at least {floor:.0f} ({lo:.0f} per 10 min)")
            if not allow_thin:
                raise ToolError(msg + " — pass allow_thin=True if the film is genuinely quiet")
            log(f"cues: {msg} (allowed: allow_thin)")


def _transition_ids(manifest: dict) -> set[str]:
    return {entry.split()[0].replace("·", "")
            for entry in manifest["monoElements"]["transitions"]["ids"]}


def _duration_of(video: str) -> float | None:
    """Runtime of the video, or None if it can't be probed.

    Only the per-10-minutes budget needs it, so an unprobeable file loses that one
    check rather than the whole gate.
    """
    try:
        value = media.ffprobe_json(video).get("format", {}).get("duration")
        return float(value) if value else None
    except Exception:
        return None


# --- compositing ---------------------------------------------------------------

def _filter_graph(plan: list[dict]) -> str:
    """Every cue lands 1:1 at 0,0 for exactly its window.

    No scaling and no added fades, unlike the b-roll path in overlays.py: these are
    full-frame compositions rendered at the project's own size, and each already
    animates its own entrance and exit. A second fade on top would double them.
    """
    parts, prev = [], "0:v"
    for i, cue in enumerate(plan):
        parts.append(f"[{i + 1}:v]setpts=PTS+{cue['start']:.3f}/TB[o{i}]")
        parts.append(
            f"[{prev}][o{i}]overlay=0:0:"
            f"enable='between(t,{cue['start']:.3f},{cue['end']:.3f})'[v{i + 1}]")
        prev = f"v{i + 1}"
    parts.append(f"[{prev}]format=yuv420p[v]")
    return ";".join(parts)


TOOL = CuesTool()
