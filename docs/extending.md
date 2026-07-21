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
