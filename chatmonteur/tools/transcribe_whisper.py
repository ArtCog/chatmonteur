"""Capability: ``transcribe`` — word-level transcript via faster-whisper (local).

The default, free, no-API-key transcription backend. Tries CUDA, falls back to
CPU. Output is a JSON with segment + word timestamps that ``cut_meaning`` and
``subtitles`` consume.
"""

from __future__ import annotations

import json

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult


class WhisperTranscribeTool(Tool):
    manifest = ToolManifest(
        name="transcribe_faster_whisper",
        capability="transcribe",
        summary="Local word-level transcription (faster-whisper). Free, no API key.",
        backends=("faster-whisper",),
        requires_py=("faster_whisper",),
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str, model: str | None = None, language: str | None = None) -> ToolResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - guarded by requires_py
            raise ToolError("faster-whisper not installed; run setup or `pip install chatmonteur[whisper]`") from exc

        model_name = model or ctx.config.transcribe.model
        lang = language or ctx.config.transcribe.language

        whisper = _load(WhisperModel, model_name, ctx.log)
        segments, info = whisper.transcribe(input, language=lang, word_timestamps=True)

        out = {"language": info.language, "duration": info.duration, "segments": []}
        for seg in segments:
            out["segments"].append(
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                    "words": [
                        {"start": w.start, "end": w.end, "word": w.word, "prob": round(w.probability, 4)}
                        for w in (seg.words or [])
                    ],
                }
            )

        path = ctx.paths.transcripts / "master.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        ctx.log(f"transcribed {len(out['segments'])} segments ({out['language']})")
        return ToolResult(artifacts={"transcript": str(path)}, meta={"language": out["language"], "segments": len(out["segments"])})


def _load(WhisperModel, model_name: str, log):  # noqa: N803
    """Prefer GPU, fall back to CPU — don't crash on machines without CUDA."""
    try:
        log(f"loading whisper '{model_name}' on cuda")
        return WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception:  # noqa: BLE001 - CUDA absent / OOM → CPU
        log(f"cuda unavailable, loading whisper '{model_name}' on cpu")
        return WhisperModel(model_name, device="cpu", compute_type="int8")


TOOL = WhisperTranscribeTool()
