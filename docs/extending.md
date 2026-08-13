# Extending chatmonteur

chatmonteur is built to grow. Two extension points, no core changes needed.

## Add a capability (a tool)

A tool wraps one engine to provide one *capability*. Drop a module in
`chatmonteur/tools/` that exposes a module-level `TOOL`:

```python
# chatmonteur/tools/denoise_deepfilter.py
from ..core.tool import Tool, ToolManifest, ToolResult
from ..core.context import RunContext
from .. import media

class DenoiseTool(Tool):
    manifest = ToolManifest(
        name="denoise_deepfilternet",
        capability="denoise",          # the capability pipelines can ask for
        summary="Neural speech denoise.",
        requires_bin=("ffmpeg",),
        requires_py=("df",),           # checked automatically
        cost="free",
    )

    def run(self, ctx: RunContext, *, input: str) -> ToolResult:
        out = ctx.paths.clips / "denoised.wav"
        # ... do the work, raise a ToolError on failure ...
        return ToolResult(artifacts={"audio": str(out)})

TOOL = DenoiseTool()
```

The registry discovers it automatically (`chatmonteur tools` will list it). If its
binaries/modules are missing, that surfaces as a clear `MissingDependencyError`
only when something actually needs the capability.

Run any discovered capability through the public front door by putting its
keyword arguments in a UTF-8 JSON object:

```bash
chatmonteur run denoise --project 2026-demo --params denoise-run.json
```

The command creates the montage project contract when needed and writes the
normal capability checkpoint. Use `--no-resume` to force a fresh execution.

**Rules of a good tool:** one capability, read everything from `RunContext`
(never hardcode paths), write only under `ctx.paths.*`, return artifacts as
`{logical_name: path}`, raise — never fail silently.

### Multiple backends for one capability

Several tools can provide the same capability (e.g. `transcribe` via
faster-whisper *and* elevenlabs). The runner prefers a tool whose requirements
are already satisfied; a pipeline step can force one with `backend: <name>`.

## Add a pipeline

A pipeline is a YAML in `pipelines/`. Steps reference capabilities; chain them
with `${step.artifact}`. The CLI seeds `${source.video}` and `${opts.lut}`.

```yaml
name: shorts
steps:
  - id: normalize
    capability: normalize
    params: { input: "${source.video}" }
  - id: transcribe
    capability: transcribe
    params: { input: "${normalize.video}" }
  - id: render
    capability: render
    params: { input: "${normalize.video}" }
```

Run it: `chatmonteur edit clip.mp4 --pipeline shorts`.

## Optional steps

Give a step `when: <flag>`; it runs only if that option is truthy. Keep the
linear chain intact (don't let a later step reference an optional step's output
unless that option is always on).

## Adding a dependency: the licence bar

chatmonteur is MIT and must stay installable by anyone, including inside a
commercial product. A dependency's licence is therefore part of its API — check
it before you write the import, not after (ADR-0004).

Verify against the actual file, never from memory or a blog post:

```
gh api repos/<owner>/<repo> --jq .license.spdx_id
```

If that returns `null` or `NOASSERTION`, read the LICENSE file yourself: no file
at all means all rights reserved (an "open-source" README is not a licence), and
custom text is usually where "academic, non-commercial use only" hides.

**Rejected outright:** AGPL, GPL, "non-commercial", "research use only", and any
project with no licence file. Fine: MIT, BSD-2/3, Apache-2.0 (keep its NOTICE),
ISC, MPL-2.0.

**The trap worth naming once, loudly: `pip install ultralytics` (YOLOv8/v11) is
AGPL-3.0.** It reads like an ordinary permissive package and is the default
building block behind most "detect X in an image" tutorials — including several
face/cursor detectors that would otherwise fit this project. AGPL obligations
attach to *use*, not just to copying, so it cannot be a dependency here at all.
Reach for MediaPipe (Apache-2.0) or dlib/face_recognition (MIT/Boost) instead.

An AGPL tool the user installs and runs themselves is a different question — that
is an arms-length external program (same posture as ffmpeg's GPL builds), not
something this tree imports.
