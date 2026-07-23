"""Smoke test for cut_edl: executing an approved EDL shortens the clip.

Run from repo root:  python tests/smoke_cut_edl.py
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

        # The agent's approved plan: remove [1.0, 2.0] from the 3s clip.
        edl = ctx.paths.transcripts / "edl.json"
        edl.write_text(json.dumps({"removed": [[1.0, 2.0]]}), encoding="utf-8")

        res = reg.get("cut_edl_ffmpeg").run(ctx, input=str(raw), edl=str(edl))
        out = res.artifacts["video"]
        out_dur = float(media.ffprobe_json(out)["format"]["duration"])
        print(f"cut_edl -> {res.meta}; actual out duration={out_dur:.2f}s")
        assert 1.8 < out_dur < 2.3, f"expected ~2s clip, got {out_dur}s"
        assert res.meta["ranges"] == 2, res.meta
        print("PASS: cut_edl executes an approved EDL")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
