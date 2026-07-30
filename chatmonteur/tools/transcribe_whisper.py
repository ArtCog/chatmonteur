"""Capability: ``transcribe`` — word-level transcript via faster-whisper (local).

The default, free, no-API-key transcription backend. Tries CUDA, falls back to
CPU. Output is a JSON with segment + word timestamps that the agent (cut-plan) and
``subtitles`` consume.

Three things happen between Whisper and that JSON, because raw ASR output is not
safe to burn into a video:

1. **A language guard.** An ``.en`` model given Russian audio does not fail — it
   silently *translates*. The whole transcript comes back in fluent English and
   nothing about it looks wrong until the captions are already burned.
2. **A hallucination filter.** Whisper invents text over silence and music:
   musical-note runs, ``♪``, replacement characters, sub-100 ms grunts. The last
   dogfood run put "СИГНАЛ СМС" on screen this way. Individually these are
   dropped; when they dominate the transcript the run is declared FAILED rather
   than patched, because a transcript that hallucinated once will hallucinate in
   places nobody checks.
3. **A correction dictionary** (``assets/brand/asr_fixes.yaml``). Whisper has
   never heard "ИИмерсивный". A misspelled brand term in a caption is the most
   visible amateur signal there is, and no model size fixes it.
"""

from __future__ import annotations

import json
import pathlib
import re

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult

# Whisper's signature inventions over silence: musical notes and the Unicode
# replacement character.
_JUNK = re.compile(r"[♩-♯�]")
_ONLY_JUNK = re.compile(r"^[\s♩-♯�.,!?-]*$")
_FILLER = re.compile(r"^\s*(huh|uh|um+|ah+|oh+|hm+|мм+|эм+|ээ+)[\s.!?…]*$", re.IGNORECASE)
_FILLER_MAX = 0.1        # a "word" shorter than this is a breath, not speech
_JUNK_SHARE_FAILED = 0.2  # above this the transcription is broken, not dirty
_UNRELIABLE_SPAN = 0.05   # word timings tighter than this are reported, never fixed
# Whisper's own verdict on a segment. A plausible-looking hallucination cannot be
# spotted by pattern — "СИГНАЛ СМС" is ordinary Russian — but the model already
# knows it heard nothing. These are Whisper's own decoding thresholds.
_NO_SPEECH = 0.6
_LOW_LOGPROB = -1.0

_PUNCT_HEAD = "«(\"'“„-—"
_PUNCT_TAIL = ".,!?;:…»)\"'”"

_FIXES_FILE = "asr_fixes.yaml"


class WhisperTranscribeTool(Tool):
    manifest = ToolManifest(
        name="transcribe_faster_whisper",
        capability="transcribe",
        summary="Local word-level transcription (faster-whisper). Free, no API key.",
        backends=("faster-whisper",),
        requires_py=("faster_whisper",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        model: str | None = None,
        language: str | None = None,
        fixes: str | None = None,
    ) -> ToolResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - guarded by requires_py
            raise ToolError("faster-whisper not installed; run setup or `pip install chatmonteur[whisper]`") from exc

        model_name = model or ctx.config.transcribe.model
        lang = language or ctx.config.transcribe.language
        _check_language(model_name, lang)

        whisper = _load(WhisperModel, model_name, ctx.log)
        segments, info = whisper.transcribe(input, language=lang, word_timestamps=True)

        raw = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                # the model's own confidence — the only thing that catches a
                # hallucination that reads like ordinary speech
                "no_speech_prob": getattr(seg, "no_speech_prob", 0.0),
                "avg_logprob": getattr(seg, "avg_logprob", 0.0),
                "words": [
                    {"start": w.start, "end": w.end, "word": w.word, "prob": round(w.probability, 4)}
                    for w in (seg.words or [])
                ],
            }
            for seg in segments
        ]

        clean, dropped = _drop_hallucinations(raw, model_name, log=ctx.log)
        table = _load_fixes(ctx, fixes)
        clean, fixed = _apply_fixes(clean, table)
        shaky = _unreliable_words(clean)

        out = {"language": info.language, "duration": info.duration, "segments": clean}
        path = ctx.paths.transcripts / "master.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        ctx.log(f"transcribed {len(clean)} segments ({out['language']})"
                + (f", dropped {dropped} hallucinated" if dropped else "")
                + (f", corrected {fixed} brand terms" if fixed else ""))
        if shaky:
            # Reported, never auto-corrected: a wrong timestamp silently moved is
            # worse than a wrong timestamp the agent knows about.
            ctx.log(f"⚠ {shaky} words have timings under {_UNRELIABLE_SPAN}s — "
                    "treat their word-level positions as approximate")
        return ToolResult(
            artifacts={"transcript": str(path)},
            meta={"language": out["language"], "segments": len(clean),
                  "dropped": dropped, "corrected": fixed, "unreliable_words": shaky},
        )


def _check_language(model_name: str, lang: str | None) -> None:
    """An ``.en`` model does not refuse other languages — it translates them.

    This is the failure that looks like success: a fluent English transcript of
    Russian audio, discovered only once it is on screen.
    """
    if model_name.endswith(".en") and (lang or "en") != "en":
        raise ToolError(
            f"model '{model_name}' is English-only and would silently TRANSLATE "
            f"{lang!r} audio instead of transcribing it. Use '{model_name[:-3]}'."
        )


def _drop_hallucinations(segments: list[dict], model_name: str, log=None) -> tuple[list[dict], int]:
    """Remove invented segments; refuse the whole transcript if they dominate."""
    junky = sum(1 for s in segments if _JUNK.search(s.get("text", "")))
    if segments and junky / len(segments) > _JUNK_SHARE_FAILED:
        raise ToolError(
            f"transcription failed: {junky}/{len(segments)} segments are musical notes or "
            f"replacement characters. This is not repairable by filtering — re-run with a "
            f"larger model than '{model_name}', or check that the audio actually has speech."
        )
    kept = []
    for s in segments:
        why = _why_invented(s)
        if why:
            if log:
                log(f"  dropped [{s['start']:.1f}s] {s.get('text', '')[:40]!r} — {why}")
            continue
        kept.append(s)
    return kept, len(segments) - len(kept)


def _why_invented(seg: dict) -> str | None:
    """Reason this segment is not real speech, or None if it is.

    The last dogfood run burned "СИГНАЛ СМС" into a caption. No pattern catches
    that — it is ordinary Russian. What catches it is that Whisper reported the
    audio underneath as silence while emitting it anyway, so the model's own
    ``no_speech_prob`` / ``avg_logprob`` are the load-bearing test and the regex
    rules are only the second net.
    """
    text = (seg.get("text") or "").strip()
    if not text or _ONLY_JUNK.match(text):
        return "empty or musical notes only"
    if _JUNK.search(text):
        # A replacement character or a note glyph inside otherwise plausible text
        # means part of it was never decoded — the whole segment is untrustworthy.
        return "contains undecodable characters"
    if _FILLER.match(text) and (seg["end"] - seg["start"]) < _FILLER_MAX:
        return "sub-100ms filler sound"
    if (seg.get("no_speech_prob", 0.0) > _NO_SPEECH
            and seg.get("avg_logprob", 0.0) < _LOW_LOGPROB):
        return (f"model heard silence (no_speech={seg['no_speech_prob']:.2f}, "
                f"logprob={seg['avg_logprob']:.2f})")
    return None


def _unreliable_words(segments: list[dict]) -> int:
    return sum(
        1
        for s in segments
        for w in s.get("words") or []
        if (w.get("end", 0) - w.get("start", 0)) < _UNRELIABLE_SPAN
    )


# --- the correction dictionary --------------------------------------------------

def _load_fixes(ctx: RunContext, override: str | None) -> dict[str, str]:
    """Read the correction table; an absent file just means no corrections."""
    if override:
        path = pathlib.Path(override)
        if not path.is_file():
            raise ToolError(f"asr fixes file not found: {path}")
    else:
        path = pathlib.Path(__file__).resolve().parents[2] / "assets" / "brand" / _FIXES_FILE
        if not path.is_file():
            return {}
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ToolError(f"{path} must be a flat mapping of misheard -> correct")
    return {str(k).strip().lower(): str(v) for k, v in data.items()}


def _split_token(raw: str) -> tuple[str, str, str, str]:
    """Break a Whisper token into (leading space, opening punctuation, word, closing).

    Whisper emits words with a leading space; keeping the pieces apart is what lets
    a correction land without eating the punctuation around it.
    """
    body = raw.strip()
    lead = raw[: len(raw) - len(raw.lstrip())]
    head = ""
    while body and body[0] in _PUNCT_HEAD:
        head, body = head + body[0], body[1:]
    tail = ""
    while body and body[-1] in _PUNCT_TAIL:
        tail, body = body[-1] + tail, body[:-1]
    return lead, head, body, tail


def _apply_fixes(segments: list[dict], fixes: dict[str, str]) -> tuple[list[dict], int]:
    """Replace misheard terms, longest phrase first.

    A matched span COLLAPSES into one token spanning the whole time range. That
    keeps the timeline honest when the replacement has a different word count than
    the mistake ("опен роутер" -> "OpenRouter"), and it makes a brand name
    highlight as a unit in karaoke captions, which is what it is.
    """
    if not fixes:
        return segments, 0
    longest = max(len(k.split()) for k in fixes)
    changed = 0

    for seg in segments:
        words = seg.get("words") or []
        if not words:
            # No word timings (a short or noisy segment): fall back to the text.
            seg["text"], n = _fix_text(seg.get("text", ""), fixes)
            changed += n
            continue

        out: list[dict] = []
        i = 0
        while i < len(words):
            for n in range(min(longest, len(words) - i), 0, -1):
                span = words[i: i + n]
                parts = [_split_token(w["word"]) for w in span]
                phrase = " ".join(p[2] for p in parts).lower()
                if phrase in fixes:
                    lead, head = parts[0][0], parts[0][1]
                    tail = parts[-1][3]
                    out.append({
                        "start": span[0]["start"], "end": span[-1]["end"],
                        "word": f"{lead}{head}{fixes[phrase]}{tail}",
                        "prob": min(w.get("prob", 1.0) for w in span),
                    })
                    i += n
                    # an entry whose key already matches its value (a spelling the
                    # dictionary confirms) is not a correction — don't report it
                    changed += fixes[phrase] != " ".join(p[2] for p in parts)
                    break
            else:
                out.append(words[i])
                i += 1
        seg["words"] = out
        seg["text"] = "".join(w["word"] for w in out).strip()
    return segments, changed


def _fix_text(text: str, fixes: dict[str, str]) -> tuple[str, int]:
    """Whole-word replacement over plain text, for segments with no word timings."""
    changed = 0
    for key in sorted(fixes, key=lambda k: -len(k)):
        pattern = re.compile(rf"(?<!\w){re.escape(key)}(?!\w)", re.IGNORECASE)
        text, n = pattern.subn(fixes[key], text)
        changed += n
    return text, changed


def _load(WhisperModel, model_name: str, log):  # noqa: N803
    """Prefer GPU, fall back to CPU — don't crash on machines without CUDA."""
    try:
        log(f"loading whisper '{model_name}' on cuda")
        return WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception:  # noqa: BLE001 - CUDA absent / OOM → CPU
        log(f"cuda unavailable, loading whisper '{model_name}' on cpu")
        return WhisperModel(model_name, device="cpu", compute_type="int8")


TOOL = WhisperTranscribeTool()
