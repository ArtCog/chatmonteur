"""Smoke test the full `chatmonteur edit` pipeline end-to-end on a synthetic clip.

Run from repo root:  python tests/smoke_cli.py
Uses the tiny whisper model. Verifies a final render is produced.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatmonteur.cli import main  # noqa: E402


def make_clip(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-shortest", str(path)],
        check=True,
    )


def run() -> int:
    tmp = Path(tempfile.mkdtemp())
    try:
        clip = tmp / "talk.mp4"
        make_clip(clip)

        print("--- chatmonteur tools ---")
        assert main(["tools"]) == 0

        print("\n--- chatmonteur edit ---")
        rc = main(["edit", str(clip), "--root", str(tmp), "--model", "tiny"])
        assert rc == 0, f"edit exited {rc}"

        final = tmp / "projects" / "talk" / "renders" / "final.mp4"
        assert final.is_file(), f"no final render at {final}"
        print(f"\nPASS: full pipeline produced {final.name} ({final.stat().st_size} bytes)")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(run())
