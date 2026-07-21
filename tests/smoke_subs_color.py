"""Smoke test for subtitles (burn) and color (LUT) on a synthetic clip.

Run from repo root:  python tests/smoke_subs_color.py
"""

from __future__ import annotations

import json
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

        # hand-made transcript (synthetic clip has no speech)
        tr_path = ctx.paths.transcripts / "master.json"
        tr_path.write_text(json.dumps({
            "language": "en", "duration": 3,
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello from chatmonteur", "words": []},
                {"start": 1.5, "end": 3.0, "text": "captions and color work", "words": []},
            ],
        }), encoding="utf-8")

        subs = reg.get("subtitles_ffmpeg").run(ctx, input=str(raw), transcript=str(tr_path))
        assert Path(subs.artifacts["srt"]).exists() and Path(subs.artifacts["video"]).exists()
        print(f"subtitles OK -> {subs.meta}")

        col = reg.get("color_lut3d_ffmpeg").run(ctx, input=str(raw), lut="warm_film")
        assert Path(col.artifacts["video"]).exists()
        print(f"color OK -> {col.meta}")

        print("PASS: subtitles + color")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
