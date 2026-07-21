"""Capability: ``cut_meaning`` — remove filler words and long pauses by transcript.

Our own engine-independent cutting (video-use has no programmatic API). From a
word-level transcript it builds a keep-list (EDL), then cuts in a SINGLE ffmpeg
pass with ``trim``/``atrim`` + ``concat`` — frame-accurate, no select-filter
desync, never stream-copied. Writes the EDL so the agent can show a cut-plan
for approval before rendering.
"""

from __future__ import annotations

import json
import re

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

# Default filler vocab (English + Russian). Override via params.
_FILLERS = {
    "um", "uh", "uhm", "erm", "hmm", "like", "literally",
    "эээ", "ээ", "ммм", "мм", "эм", "ну", "типа", "вот", "значит", "короче",
}
_PUNCT = re.compile(r"[^\w']+", re.UNICODE)


class CutMeaningTool(Tool):
    manifest = ToolManifest(
        name="cut_meaning_transcript",
        capability="cut_meaning",
        summary="Remove fillers + long pauses from a transcript, cut in one ffmpeg pass.",
        backends=("transcript",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        transcript: str,
        pause_max: float = 0.7,
        keep_pad: float = 0.12,
        fillers: list[str] | None = None,
    ) -> ToolResult:
        media.require("ffmpeg")
        data = json.loads(open(transcript, encoding="utf-8").read())
        words = [w for seg in data.get("segments", []) for w in seg.get("words", [])]
        duration = float(data.get("duration") or media.ffprobe_json(input)["format"]["duration"])
        vocab = {f.lower() for f in (fillers or _FILLERS)}

        removed = _removed_intervals(words, vocab, pause_max, keep_pad)
        keep = _invert(removed, duration, min_len=0.10)
        if not keep:
            raise ToolError("cut_meaning would remove everything — check transcript/thresholds")

        edl_path = ctx.paths.transcripts / "edl.json"
        edl_path.write_text(json.dumps({"keep": keep, "removed": removed}, indent=2), encoding="utf-8")

        out = ctx.paths.clips / "cut.mp4"
        if len(keep) == 1 and keep[0] == [0.0, round(duration, 3)]:
            ctx.log("cut_meaning: nothing to remove")
        encoder = media.detect_encoder(ctx.config.encode.encoder)
        media.run(_cut_cmd(input, keep, out, encoder), log=ctx.log, desc=f"cut by meaning ({len(keep)} kept ranges)")

        kept_dur = round(sum(b - a for a, b in keep), 2)
        ctx.log(f"kept {kept_dur}s of {round(duration, 2)}s in {len(keep)} ranges")
        return ToolResult(
            artifacts={"video": str(out), "edl": str(edl_path)},
            meta={"kept_seconds": kept_dur, "source_seconds": round(duration, 2), "ranges": len(keep)},
        )


def _norm(word: str) -> str:
    return _PUNCT.sub("", word).strip().lower()


def _removed_intervals(words, vocab, pause_max, keep_pad):
    removed: list[list[float]] = []
    for w in words:
        if _norm(w.get("word", "")) in vocab:
            removed.append([float(w["start"]), float(w["end"])])
    for a, b in zip(words, words[1:]):
        gap = float(b["start"]) - float(a["end"])
        if gap > pause_max:
            removed.append([float(a["end"]) + keep_pad, float(b["start"]) - keep_pad])
    return _merge([r for r in removed if r[1] > r[0]])


def _merge(intervals):
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


def _invert(removed, duration, min_len):
    keep, cursor = [], 0.0
    for a, b in removed:
        if a - cursor >= min_len:
            keep.append([round(cursor, 3), round(a, 3)])
        cursor = max(cursor, b)
    if duration - cursor >= min_len:
        keep.append([round(cursor, 3), round(duration, 3)])
    return keep


def _cut_cmd(src, keep, out, encoder):
    parts, labels = [], []
    for i, (a, b) in enumerate(keep):
        parts.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    concat = f"{''.join(labels)}concat=n={len(keep)}:v=1:a=1[v][a]"
    fc = ";".join(parts + [concat])
    return [
        "ffmpeg", "-y", "-i", str(src),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", encoder, *media.encoder_quality_args(encoder),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ]


TOOL = CutMeaningTool()
