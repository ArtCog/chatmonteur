---
project_title: "{{PROJECT_TITLE}}"
montage_status: intake
legacy_source_root: "{{LEGACY_SOURCE_ROOT}}"
---

# {{PROJECT_TITLE}}

This file is the first read for every agent entering this video project.

## Current state

- Stage: ingest
- Next step: import source media and run the mechanical skeleton.
- Approval gates: meaning cut, voice tempo, storyboard, optional subtitles, and mix test.

## File contract

- `raw/` — immutable source recordings; never edit or overwrite them.
- `assets/` — project-specific screenshots, b-roll, and licensed media.
- `clips/` — reproducible technical and editorial intermediates.
- `transcripts/` — ASR, EDL, cue plans, and the approved `storyboard.json`.
- `compositions/` — HyperFrames sources and alpha renders.
- `previews/` — approval-gate samples; never call these final.
- `renders/` — masters and QC evidence only.

## Project identity and constraints

- Canonical project root: this directory.
- Legacy source root: `{{LEGACY_SOURCE_ROOT}}`
- `canvas.json` is optional and is created only when the Planning Canvas is used.

## Montage decisions

Record source selection, cut decisions, approved timing, storyboard, exact on-screen wording,
subtitle choice, mix approval, render status, and unresolved montage decisions here.
