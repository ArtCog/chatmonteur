"""Capability: ``qc`` — the blocking gate on the finished file.

The last step of every pipeline, and the only one whose job is to say **no**.
It re-opens the rendered file as a stranger would and refuses to hand it over if
it is broken in a way a viewer would notice in the first ten seconds.

Why a gate and not a warning: a warning scrolls past in a log and the file gets
delivered anyway. Both real failures on this project shipped exactly that way —
a file whose audio would not play, and a cut that quietly lost half its runtime.
Every rule below is a boolean; any ``fail`` stops the pipeline.

What it inspects
----------------
* **Container / streams** — readable, has video, has audio, sane frame size.
* **Frames at 10/35/65/90 %** — deliberately not the head and tail, where an
  intro or an end card is black on purpose. Mean luma under ``_BLACK_YAVG``
  means the viewer is looking at nothing.
* **Levels** — ``mean_volume`` catches a silent track (right length, no sound),
  ``max_volume`` catches clipping.
* **Duration drift** — an encode must not change the runtime it was handed. Pass
  ``expected`` (seconds, or the path of the file the render was made from).

The report lands next to the file as ``<stem>.qc.json`` **before** anything is
raised, so the evidence outlives the failure.

Measuring and judging are separate on purpose: ``_probe`` touches ffmpeg,
``_judge`` is pure. Every rule is therefore testable without a media file.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

# Where to look. Not 0 % / 100 %: a fade-in and an end card are black by design,
# and sampling them would fail every well-made video.
_FRAME_POSITIONS = (0.10, 0.35, 0.65, 0.90)
# Mean luma below this = the frame reads as black. NOT 16: video is encoded in
# limited (broadcast) range, where pure black is Y=16 exactly, so a `< 16` test
# never fires on a real black frame. Measured on our own colours: #000000 → 16,
# brand background #0B0B0C → 26, #0B0F0E → 28. 20 catches black and crushed
# near-black while leaving a dark brand card six points of headroom.
_BLACK_YAVG = 20.0
_SILENT_DBFS = -60.0      # mean volume under this = the track plays nothing
_CLIP_DBFS = -0.5         # peak above this = clipped samples
_MAX_DRIFT = 0.25         # 25 % runtime change between what went in and what came out
_MIN_DURATION = 1.0
_MIN_W, _MIN_H = 320, 240


class QCTool(Tool):
    manifest = ToolManifest(
        name="qc_ffmpeg",
        capability="qc",
        summary="Block delivery of a broken render: black frames, silence, clipping, drift.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg", "ffprobe"),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        expected: str | float | None = None,
        strict: bool = True,
    ) -> ToolResult:
        media.require("ffmpeg")
        path = pathlib.Path(input)
        if not path.is_file():
            raise ToolError(f"qc: nothing to check, {path} does not exist")

        facts = _probe(path, log=ctx.log)
        issues = _judge(facts, _expected_seconds(expected))
        failed = [i for i in issues if i["severity"] == "fail"]

        report = {
            "status": "fail" if failed else "pass",
            "recommended_action": "re_render" if failed else "ship",
            "file": str(path),
            "checks": facts,
            "issues": issues,
        }
        report_path = path.with_suffix(".qc.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if failed:
            detail = "\n".join(f"  ✗ {i['check']}: {i['detail']}" for i in failed)
            msg = (f"QC FAILED on {path.name} ({len(failed)} blocking):\n{detail}\n"
                   f"  report: {report_path}")
            if strict:
                raise ToolError(msg)
            ctx.log(msg)
        else:
            warned = len(issues)
            ctx.log(f"qc: {path.name} passed" + (f" ({warned} warnings)" if warned else ""))
        return ToolResult(
            artifacts={"video": str(path), "qc_report": str(report_path)},
            meta=report,
        )


# --- judging (pure) -------------------------------------------------------------

def _judge(facts: dict, expected: float | None) -> list[dict]:
    """Turn measurements into a verdict. No I/O — this is the rule set itself."""
    issues: list[dict] = []
    if not facts.get("readable"):
        return [_fail("container", facts.get("probe_error") or "ffprobe cannot read the file")]

    duration = float(facts.get("duration") or 0.0)
    if duration < _MIN_DURATION:
        issues.append(_fail("duration", f"{duration:.2f}s is not a video"))

    w, h = facts.get("width") or 0, facts.get("height") or 0
    if not w or not h:
        issues.append(_fail("video_stream", "no video stream"))
    elif w < _MIN_W or h < _MIN_H:
        issues.append(_fail("low_res", f"{w}x{h} is below {_MIN_W}x{_MIN_H}"))

    if not facts.get("has_audio"):
        issues.append(_fail("no_audio", "no audio stream — a talking-head render must carry sound"))
    else:
        mean, peak = facts.get("mean_volume_db"), facts.get("max_volume_db")
        if mean is None:
            issues.append(_fail("no_audio", "audio stream present but volumedetect measured nothing"))
        elif mean < _SILENT_DBFS:
            issues.append(_fail("silent", f"mean volume {mean} dBFS — the track plays nothing"))
        if peak is not None and peak > _CLIP_DBFS:
            issues.append(_fail("clipping", f"peak {peak} dBFS is into the ceiling"))

    luma = facts.get("frame_luma") or {}
    if duration >= _MIN_DURATION and w and h:
        if len(luma) < len(_FRAME_POSITIONS):
            issues.append(_fail(
                "undecodable",
                f"only {len(luma)}/{len(_FRAME_POSITIONS)} probe frames decoded — the file is damaged",
            ))
        for pos, value in luma.items():
            if value < _BLACK_YAVG:
                issues.append(_fail("black_frame", f"frame at {pos} is black (luma {value:.1f})"))

    if expected is None:
        issues.append(_warn("duration_drift", "no expected duration given — runtime went unchecked"))
    elif expected > 0 and duration:
        drift = abs(duration - expected) / expected
        if drift > _MAX_DRIFT:
            issues.append(_fail(
                "duration_drift",
                f"{duration:.1f}s vs expected {expected:.1f}s ({drift:.0%}) — "
                "the render lost or gained content",
            ))
    return issues


def _fail(check: str, detail: str) -> dict:
    return {"check": check, "severity": "fail", "detail": detail}


def _warn(check: str, detail: str) -> dict:
    return {"check": check, "severity": "warn", "detail": detail}


# --- measuring (touches ffmpeg) -------------------------------------------------

def _probe(path: pathlib.Path, log) -> dict:
    facts: dict = {"readable": True}
    try:
        info = media.ffprobe_json(path)
    except ToolError as exc:
        return {"readable": False, "probe_error": str(exc)}

    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    duration = float(info.get("format", {}).get("duration") or 0.0)
    facts["duration"] = round(duration, 3)
    facts["has_audio"] = any(s.get("codec_type") == "audio" for s in streams)
    if video is not None:
        facts["width"] = int(video.get("width") or 0)
        facts["height"] = int(video.get("height") or 0)

    if facts["has_audio"]:
        vol = media.volume_stats(path)
        facts["mean_volume_db"] = vol.get("mean")
        facts["max_volume_db"] = vol.get("max")
    if video is not None and duration >= _MIN_DURATION:
        facts["frame_luma"] = _sample_luma(path, duration, log=log)
    return facts


def _sample_luma(path: pathlib.Path, duration: float, log) -> dict[str, float]:
    """Mean luma of one frame at each probe position, keyed by position label.

    ``signalstats`` computes it and ``metadata=print`` dumps the tag to stdout;
    seeking with ``-ss`` *before* ``-i`` keeps each probe near-instant even on a
    long file. A position that fails to decode is simply absent from the result —
    the caller reads a short dict as damage, which is the point.
    """
    out: dict[str, float] = {}
    for frac in _FRAME_POSITIONS:
        at = duration * frac
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{at:.3f}", "-i", str(path), "-frames:v", "1",
             "-vf", "signalstats,metadata=print:file=-", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        for line in (proc.stdout or "").splitlines():
            if "signalstats.YAVG" in line:
                try:
                    out[f"{frac:.0%}"] = float(line.split("=")[1])
                except (IndexError, ValueError):
                    pass
                break
        else:
            log(f"qc: no frame decoded at {at:.1f}s")
    return out


def _expected_seconds(expected: str | float | None) -> float | None:
    """``expected`` is a number of seconds, or the path of the file the render was
    made FROM — probing that file is the honest reference, since an encode must
    not change the runtime it was handed."""
    if expected is None:
        return None
    if isinstance(expected, (int, float)):
        return float(expected)
    p = pathlib.Path(str(expected))
    if p.is_file():
        try:
            return float(media.ffprobe_json(p)["format"]["duration"])
        except (ToolError, KeyError, ValueError):
            return None
    try:
        return float(expected)
    except ValueError:
        return None


TOOL = QCTool()
