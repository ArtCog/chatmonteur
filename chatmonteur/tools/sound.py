"""Capability: ``sound`` — music bed, ducking under speech, and SFX hits.

The layer that separates "a script cut the pauses" from "an editor finished this".
The AGENT decides WHAT plays and WHERE (music mood, which beats get a hit); this
tool executes the mix with the engineering that makes it sound professional:

* **Ducking is sidechain compression, not a volume dip.** The speech track is
  split (``asplit``): one copy plays, one drives a compressor on the music. Music
  gets out of the way exactly while a word is spoken and returns in the gaps.
* **The music is EQ-notched at 2–4 kHz** — the speech-intelligibility band. This
  matters more than level: a bed that is merely quiet still masks consonants.
* **An SFX lands slightly BEFORE its visual cut** (``_SFX_LEAD``). The brain
  registers sound faster than picture, so a sample aligned on the exact frame
  reads as late.
* **Loudness is NOT set here.** ``render`` applies loudnorm last, per the
  production rule "loudness is the final audio step" — normalising mid-chain and
  again at the end double-compresses the dialogue.

Plan (JSON or kwargs, authored by the agent)::

    {"music": {"file": "bed.mp3", "gain_db": -20},
     "sfx": [{"at": 12.4, "file": "whoosh.wav", "gain_db": -15}]}
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

# --- the numbers that make a mix sound professional ----------------------------
# Music sits ~20 dB under dialogue while speaking (W3C accessibility puts the floor
# at 20 dB below foreground speech; broadcast practice pulls a few more).
_MUSIC_GAIN_DB = -20.0
# Sidechain duck: a high ratio with a slow-ish release keeps the bed from pumping
# between words, while attack stays fast enough not to clip the first syllable.
_DUCK_RATIO = 9
_DUCK_ATTACK_MS = 200
_DUCK_RELEASE_MS = 500
_DUCK_THRESHOLD = 0.02      # linear amplitude (≈ −34 dBFS), not dB
# The speech band. Notching the bed here buys intelligibility that level alone can't.
_SPEECH_BAND_HZ = 3000
_SPEECH_BAND_OCT = 1.6
_SPEECH_NOTCH_DB = -4.0
_SFX_GAIN_DB = -15.0
# Sound is perceived faster than picture: land the hit just before the cut.
_SFX_LEAD = 0.015
_FADE = 1.5                 # music fade in/out, seconds


class SoundTool(Tool):
    manifest = ToolManifest(
        name="sound_ffmpeg",
        capability="sound",
        summary="Mix a ducked music bed and SFX hits under the speech track.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        plan: str | None = None,
        music: str | None = None,
        music_gain_db: float = _MUSIC_GAIN_DB,
        sfx: list | None = None,
        duck: bool = True,
        name: str = "sounded.mp4",
    ) -> ToolResult:
        media.require("ffmpeg")
        spec = _load_plan(plan) if plan else {}
        music_spec = spec.get("music") or ({"file": music} if music else None)
        sfx_list = spec.get("sfx", sfx or [])
        if not music_spec and not sfx_list:
            ctx.log("sound: nothing to mix, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"music": False, "sfx": 0})

        duration = float(media.ffprobe_json(input)["format"]["duration"])
        inputs: list[str] = [str(input)]
        graph: list[str] = []
        mix_labels: list[str] = []

        # Speech is the reference. When ducking, it must be split: one branch is
        # mixed, the other is only a control signal for the compressor.
        if music_spec and duck:
            graph.append("[0:a]asplit=2[sp][key]")
            speech_label, key_label = "[sp]", "[key]"
        else:
            speech_label, key_label = "[0:a]", None
        mix_labels.append(speech_label)

        if music_spec:
            mfile = pathlib.Path(music_spec["file"])
            if not mfile.is_file():
                raise ToolError(f"music not found: {mfile}")
            gain = float(music_spec.get("gain_db", music_gain_db))
            # Start the bed at its liveliest stretch instead of a quiet intro.
            offset = music_spec.get("offset")
            if offset is None:
                offset = _best_segment(mfile, duration, log=ctx.log)
            inputs += ["-ss", f"{offset:.2f}", "-i", str(mfile)]
            fade_out_at = max(0.0, duration - _FADE)
            graph.append(
                f"[1:a]atrim=duration={duration:.3f},asetpts=N/SR/TB,"
                # notch the speech band, then set level, then fade (fading before any
                # delay/trim would otherwise fade silence rather than audio)
                f"equalizer=f={_SPEECH_BAND_HZ}:width_type=o:width={_SPEECH_BAND_OCT}:g={_SPEECH_NOTCH_DB},"
                f"volume={gain}dB,"
                f"afade=t=in:d={_FADE},afade=t=out:st={fade_out_at:.3f}:d={_FADE}[music]"
            )
            if duck:
                graph.append(
                    f"[music]{key_label}sidechaincompress="
                    f"threshold={_DUCK_THRESHOLD}:ratio={_DUCK_RATIO}:"
                    f"attack={_DUCK_ATTACK_MS}:release={_DUCK_RELEASE_MS}:"
                    "level_sc=1:mix=0.9[ducked]"
                )
                mix_labels.append("[ducked]")
            else:
                mix_labels.append("[music]")

        for i, hit in enumerate(sfx_list):
            f = pathlib.Path(hit["file"])
            if not f.is_file():
                raise ToolError(f"SFX not found: {f}")
            idx = _next_input_index(inputs)
            inputs += ["-i", str(f)]
            at_ms = _sfx_delay_ms(float(hit["at"]))
            g = float(hit.get("gain_db", _SFX_GAIN_DB))
            graph.append(
                f"[{idx}:a]volume={g}dB,adelay={at_ms}|{at_ms}[sfx{i}]"
            )
            mix_labels.append(f"[sfx{i}]")

        # normalize=0: amix otherwise divides every input by their count, quietly
        # dropping the dialogue ~6 dB per extra layer.
        graph.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:normalize=0:"
            "dropout_transition=0[aout]"
        )
        out = ctx.paths.clips / name
        media.run(
            ["ffmpeg", "-y", *_expand(inputs),
             "-filter_complex", ";".join(graph),
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
             str(out)],
            log=ctx.log,
            desc=f"mix sound ({'music+duck' if music_spec and duck else 'music' if music_spec else 'sfx'}"
                 f", {len(sfx_list)} sfx)",
        )
        return ToolResult(
            artifacts={"video": str(out)},
            meta={"music": bool(music_spec), "ducked": bool(music_spec and duck),
                  "sfx": len(sfx_list)},
        )


def _expand(inputs: list[str]) -> list[str]:
    """The first entry is the video path; the rest already carry their own flags."""
    return ["-i", inputs[0], *inputs[1:]]


def _sfx_delay_ms(at: float) -> int:
    """Where the sample actually starts — a touch EARLIER than the beat it marks.

    Hearing beats seeing: a hit aligned to the exact frame of a cut is perceived
    as late. Landing it ``_SFX_LEAD`` before makes picture and sound feel as one.
    """
    return max(0, round((at - _SFX_LEAD) * 1000))


def _next_input_index(inputs: list[str]) -> int:
    """ffmpeg input index = how many -i flags precede this one (video counts as 0)."""
    return 1 + sum(1 for x in inputs[1:] if x == "-i")


def _load_plan(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.is_file():
        raise ToolError(f"sound plan not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _best_segment(music: pathlib.Path, need: float, log) -> float:
    """Find where in a long track the most energetic ``need`` seconds start.

    Stock beds usually open with a sparse intro; dropping that in favour of the
    liveliest stretch is the difference between a bed that supports the edit and
    one that sounds like it is still loading. Measured with ffmpeg's ebur128
    momentary loudness, then a sliding-window average.
    """
    try:
        proc = subprocess.run(
            ["ffmpeg", "-v", "info", "-i", str(music), "-af", "ebur128", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace", timeout=120,
        )
        loud = [float(m) for m in re.findall(r"M:\s*(-?\d+\.?\d*)", proc.stderr)]
    except Exception:  # noqa: BLE001 — analysis is a nicety, never a blocker
        return 0.0
    if len(loud) < 20:
        return 0.0
    per_sec = 10  # ebur128 reports momentary loudness ~every 100 ms
    window = max(1, int(need * per_sec))
    if window >= len(loud):
        return 0.0
    best_i, best_avg = 0, float("-inf")
    run = sum(loud[:window])
    for i in range(1, len(loud) - window + 1):
        run += loud[i + window - 1] - loud[i - 1]
        if run > best_avg:
            best_avg, best_i = run, i
    offset = round(best_i / per_sec, 2)
    if offset:
        log(f"sound: music starts at {offset}s (liveliest stretch)")
    return offset


TOOL = SoundTool()
