"""Smoke test for cut_silence (auto-editor) and transcribe (faster-whisper, tiny).

Run from repo root:  python tests/smoke_tools.py
Downloads the whisper 'tiny' model on first run. Synthetic tone => transcript
may be empty; this verifies wiring, not transcription accuracy.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatmonteur.core import RunContext, ToolRegistry, load_config  # noqa: E402


def make_clip(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-shortest", str(path)],
        check=True,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    try:
        raw = tmp / "raw.mp4"
        make_clip(raw)
        reg = ToolRegistry().discover()
        ctx = RunContext.for_project(load_config(str(tmp)), "smoke")

        cut = reg.get("cut_silence_auto_editor").run(ctx, input=str(raw))
        assert Path(cut.artifacts["video"]).exists(), "cut_silence produced no file"
        print(f"cut_silence OK -> {cut.meta}")

        tr = reg.get("transcribe_faster_whisper").run(ctx, input=str(raw), model="tiny")
        assert Path(tr.artifacts["transcript"]).exists(), "transcript missing"
        print(f"transcribe OK -> {tr.meta}")

        print("PASS: cut_silence + transcribe wired")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
