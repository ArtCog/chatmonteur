"""Manual smoke test: synthetic clip → normalize → render, via the real runner.

Run from repo root:  python tests/smoke_ffmpeg.py
Requires ffmpeg on PATH. Writes to a temp dir; cleans up after.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatmonteur.core import Pipeline, PipelineRunner, RunContext, ToolRegistry, load_config  # noqa: E402


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
        print(f"test clip: {raw.stat().st_size} bytes")

        reg = ToolRegistry().discover()
        print("discovered:", sorted(t.manifest.name for c in reg._by_capability.values() for t in c))

        pl = Pipeline(name="mini", steps=tuple())
        from chatmonteur.core import Step
        pl = Pipeline(
            name="mini",
            steps=(
                Step(id="normalize", capability="normalize", params={"input": str(raw)}),
                Step(id="render", capability="render", params={"input": "${normalize.video}"}),
            ),
        )

        ctx = RunContext.for_project(load_config(str(tmp)), "smoke")
        res = PipelineRunner(reg).run(ctx, pl)
        for sid, r in res.items():
            keep = {k: v for k, v in r.meta.items() if k in ("encoder", "mean_volume_db", "fps")}
            print(f"  {sid} -> {r.artifacts} | {keep}")

        final = Path(res["render"].artifacts["video"])
        assert final.exists(), "final render missing"
        level = res["render"].meta.get("mean_volume_db")
        assert level is not None and level > -60, f"output looks silent: {level} dBFS"

        # resume: second run should be fully cached (no re-encode)
        res2 = PipelineRunner(reg).run(ctx, pl)
        assert res2["render"].artifacts["video"] == str(final)
        print("PASS: end-to-end ffmpeg pipeline + resume")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
