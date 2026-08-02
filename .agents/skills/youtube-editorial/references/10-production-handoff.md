# Production handoff

Load this module only when `SCRIPT.md` is `approved_by_artur` and `approved_by: Artur`. It prepares inputs for the existing Video production owners; it does not execute production.

## VISUAL-PACK.md

Create one record per hard on-screen artifact:

```yaml
- beat_id: B03
  artifact_type: screenshot|screen_recording|source_excerpt|diagram|b_roll|asset
  source: URL or local path
  capture_instruction: exact frame, action, crop, or state
  rights_provenance: owner, license, permission, or review needed
  destination_path: work/visuals/...
  owner: Artur|agent|editor
  status: needed|capturing|ready|blocked|rejected
```

## DESIGN.md

Describe the per-video visual idea, tone, pacing, scene families, transitions, evidence treatment, and accessibility constraints. Link to shared brand guidelines for fonts, colors, logo, and recurring components; do not redefine the brand kit per video.

Explicitly do not record footage, generate subtitles, render HyperFrames, edit video, generate a thumbnail, or upload to YouTube. Route each operation through `Video/AGENTS.md` after handoff.

