"""Capability: ``cut_edl`` — execute an approved edit-decision list.

The DECISION of what to cut (fillers, false starts, retakes) is the AGENT's job:
it reasons over the verbatim word-level transcript per ``skills/cutting.md``
Tier 2 (the video-use methodology — an LLM reasons, no detector script does),
writes the plan as ``edl.json``, shows the cut-plan to the user, and only after
approval calls this tool.

This tool is deliberately dumb — the "hands": it takes the EDL and cuts in a
SINGLE ffmpeg pass with ``trim``/``atrim`` + ``concat`` — frame-accurate, no
select-filter desync, never stream-copied.

EDL format (JSON; ``keep`` wins when both keys are present):

    {"keep":    [[0.0, 12.4], [15.2, 33.0]]}
    {"removed": [[12.4, 15.2]]}
"""

from __future__ import annotations

import json
from pathlib import Path

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media


class CutEdlTool(Tool):
    manifest = ToolManifest(
        name="cut_edl_ffmpeg",
        capability="cut_edl",
        summary="Execute an approved EDL (keep/removed ranges) in one ffmpeg pass.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, edl: str, name: str = "cut.mp4") -> ToolResult:
        media.require("ffmpeg")
        edl_path = Path(edl)
        if not edl_path.is_file():
            raise ToolError(f"EDL not found: {edl_path} (the agent writes it after cut-plan approval)")
        data = json.loads(edl_path.read_text(encoding="utf-8"))
        duration = float(media.ffprobe_json(input).get("format", {}).get("duration") or 0)
        if duration <= 0:
            raise ToolError(f"cannot read duration of {input} — is it a valid video?")

        keep = _keep_ranges(data, duration)
        if not keep:
            raise ToolError("EDL leaves nothing to keep — refusing to render an empty video")

        out = ctx.paths.clips / name
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        media.run(_cut_cmd(input, keep, out, encoder), log=ctx.log, desc=f"cut EDL ({len(keep)} kept ranges)")

        kept = round(sum(b - a for a, b in keep), 2)
        ctx.log(f"kept {kept}s of {round(duration, 2)}s in {len(keep)} ranges")
        level = media.mean_volume_db(out)
        if level is not None and level < -60:
            ctx.log(f"⚠ cut output mean volume {level} dBFS looks silent — check the EDL/audio mapping")
        return ToolResult(
            artifacts={"video": str(out), "edl": str(edl_path)},
            meta={"kept_seconds": kept, "source_seconds": round(duration, 2),
                  "ranges": len(keep), "mean_volume_db": level},
        )


def _keep_ranges(data: dict, duration: float) -> list[list[float]]:
    """Normalise an EDL into a sorted, merged, clamped keep-list.

    Presence, not truthiness: an explicit ``"keep": []`` means "keep nothing" and
    must surface as the empty-video refusal — not silently fall through to a
    ``removed`` list that may also be present and mean something else entirely.
    The EDL is LLM-authored, so malformed entries get a ToolError, not a traceback.
    """
    try:
        if "keep" in data:
            keep = [[max(0.0, float(a)), min(duration, float(b))] for a, b in data["keep"]]
            return _merge([r for r in keep if r[1] - r[0] >= 0.10])
        if "removed" in data:
            removed = _merge(
                [[max(0.0, float(a)), min(duration, float(b))] for a, b in data["removed"] if float(b) > float(a)]
            )
            return _invert(removed, duration, min_len=0.10)
    except (TypeError, ValueError) as exc:
        raise ToolError(f"EDL entries must be [start, end] number pairs: {exc}") from exc
    raise ToolError("EDL must contain a 'keep' or 'removed' list")


def _merge(intervals: list[list[float]]) -> list[list[float]]:
    if not intervals:
        return []
    intervals.sort()
    out = [list(intervals[0])]
    for a, b in intervals[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _invert(removed: list[list[float]], duration: float, min_len: float) -> list[list[float]]:
    keep, cursor = [], 0.0
    for a, b in removed:
        if a - cursor >= min_len:
            keep.append([round(cursor, 3), round(a, 3)])
        cursor = max(cursor, b)
    if duration - cursor >= min_len:
        keep.append([round(cursor, 3), round(duration, 3)])
    return keep


def _cut_cmd(src: str, keep: list[list[float]], out: Path, encoder: str) -> list[str]:
    parts, labels = [], []
    for i, (a, b) in enumerate(keep):
        parts.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    concat = f"{''.join(labels)}concat=n={len(keep)}:v=1:a=1[v][a]"
    fc = ";".join(parts + [concat])
    # The graph grows with every kept range, and Windows caps a command line at
    # ~32 KB — a fine-grained EDL on a long video genuinely hits it. A script
    # file has no such ceiling.
    script = out.with_suffix(".filter")
    script.write_text(fc, encoding="utf-8")
    return [
        "ffmpeg", "-y", "-i", str(src),
        "-filter_complex_script", str(script),
        "-map", "[v]", "-map", "[a]",
        "-c:v", encoder, *media.encoder_quality_args(encoder),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k",  # 256k floor — AAC cascade is irreversible
        str(out),
    ]


TOOL = CutEdlTool()
