"""Smoke test for cut_meaning: filler + pause removal shortens the clip.

Run from repo root:  python tests/smoke_cut_meaning.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatmonteur.core import RunContext, ToolRegistry, load_config  # noqa: E402
from chatmonteur import media  # noqa: E402


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

        # word-level transcript: "um" is filler; 1.5..2.5 is a long pause.
        tr = ctx.paths.transcripts / "master.json"
        tr.write_text(json.dumps({
            "language": "en", "duration": 3.0,
            "segments": [{"start": 0, "end": 3, "text": "hello um world bye", "words": [
                {"start": 0.0, "end": 0.5, "word": "hello"},
                {"start": 0.5, "end": 1.0, "word": "um"},
                {"start": 1.0, "end": 1.5, "word": "world"},
                {"start": 2.5, "end": 3.0, "word": "bye"},
            ]}],
        }), encoding="utf-8")

        res = reg.get("cut_meaning_transcript").run(ctx, input=str(raw), transcript=str(tr))
        out = res.artifacts["video"]
        out_dur = float(media.ffprobe_json(out)["format"]["duration"])
        print(f"cut_meaning -> {res.meta}; actual out duration={out_dur:.2f}s")
        assert out_dur < 2.4, f"expected shortened clip, got {out_dur}s"
        assert res.meta["ranges"] == 3, res.meta
        print("PASS: cut_meaning removes filler + pause")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
