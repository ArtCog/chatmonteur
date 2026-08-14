# ChatMonteur architecture

ChatMonteur is the editorial orchestrator around proven media engines. It does
not replace them. Its product value is the decision layer, durable workflow,
approval gates, and verified hand-offs that turn separate tools into one
autonomous talking-head editor.

```text
source footage + editorial request
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ ChatMonteur                                                │
│ project contract · transcript reasoning · EDL · storyboard │
│ editorial intents · brand selection · approvals · QC       │
└───────┬────────────┬─────────────┬────────────┬─────────────┘
        │            │             │            │
        ▼            ▼             ▼            ▼
  auto-editor  faster-whisper  Video-Use   HyperFrames
  pause cuts   word timing     media work  motion rendering
        └────────────┴─────────────┴────────────┘
                              │
                              ▼
                     ffmpeg composition
                              │
                              ▼
                   QC evidence + final master
```

## Ownership

| Concern | Owner | ChatMonteur's responsibility |
|---|---|---|
| Pause removal | auto-editor | prepare safe audio thresholds, run per scene, preserve checkpoints |
| Transcription | faster-whisper | choose backend/model, retain word timing, apply channel term corrections |
| Media discovery/preparation | Video-Use and media providers | editorial query, rights ledger, placement, reuse history |
| Motion rendering | HyperFrames | choose the editorial intent/component, pass exact cues, composite on the source timebase |
| Visual brand | HyperFrames `frame.md` + registry blocks | select the installed brand and enforce its usage policy |
| Encode/audio/color | ffmpeg | build deterministic commands and retain one final encode path |
| Editorial judgment | ChatMonteur agent skills | cuts, emphasis, structure, evidence, pacing, sound and graphic decisions |
| Quality | ChatMonteur gates + HyperFrames check | reject weak plans, invalid graphics, broken media and uncleared delivery |

## Brand boundary

HyperFrames owns **appearance** through native `frame.md` and registry
components. ChatMonteur owns **editorial use**: why a graphic is needed, which
brand-local component serves that intent, whether source may be replaced, and
how often it may appear. See [`assets/brand/README.md`](../assets/brand/README.md)
and [ADR-0013](adr/0013-hyperframes-owns-visual-brand-chatmonteur-owns-editorial-use.md).

A palette or typography change must not require reclassifying the editing
arsenal. A genuinely different visual concept supplies different HyperFrames
components but reuses the same editorial intents, pipeline, project layout, and
QC semantics.

## Stable seams

- Every video lives in one initialized `projects/<yyyy-slug>/` contract.
- Tools expose capabilities; pipelines compose capabilities; agents make
  semantic decisions.
- External engines are versioned and upgraded through their own supported
  mechanisms, then verified before the pin changes.
- HyperFrames renders transparent intermediate graphics; ffmpeg composites them
  on the footage's timebase.
- Private channel preproduction can wrap the public montage contract but is not
  required by the open-source core.

## External engine updates

ChatMonteur pins an engine at the invocation boundary when that engine is
downloaded on demand. HyperFrames is pinned in
`chatmonteur/tools/motion_hyperframes.py`; do not replace it with a floating
`latest` runtime. To update it, compare with `npm view hyperframes version`, run
`npx hyperframes@latest upgrade --project . --check --json`, change the pin, and
pass HyperFrames `check` on representative registry, alpha-overlay, and
transition compositions before running the full ChatMonteur test suite.

System tools such as ffmpeg and Python packages are upgraded through their own
package managers, never from inside a render. Record a compatibility change in
`STATE.md`; do not make routine video output depend on whatever was published
most recently that day.

## Production data map

| Stage | Decision/tool | Durable input or plan | Output location | Gate |
|---|---|---|---|---|
| Ingest | ChatMonteur project contract | external recording | `raw/` (immutable) | source identity recorded in `PLAN.md` |
| Mechanical preparation | ffmpeg + auto-editor | source media | `clips/` | technically decodable CFR media |
| Transcript | faster-whisper | pause-cleaned clip | `transcripts/master.json` | word timing and language sanity |
| Meaning cut | agent + `cut_edl` | `master.json` | `transcripts/edl.json`, then `clips/` | human approves removals |
| Privacy | agent + ffmpeg redaction | approved regions | `transcripts/redactions.json`, then `clips/` | redacted preview inspected |
| Visual plan | agent + media/brand catalogs | final-cut transcript | `transcripts/storyboard.json` and cue plans | contact sheet/storyboard approved |
| Visual execution | ffmpeg + HyperFrames | approved storyboard/cues | `clips/`, alpha intermediates in `compositions/` | HyperFrames check + ChatMonteur plan gate |
| Sound | ffmpeg | `transcripts/sound-plan.json` + licensed assets | `clips/` | 30–40 s mix approved |
| Delivery | render + QC | approved assembled clip | `renders/` + sibling `.qc.json` | only `ship` is a deliverable |

Inside the normal storyboard call, the visual order is load-bearing:
`zooms → overlays → meaning inserts`. Camera geometry locks before placed media;
text stays above both. HyperFrames cue renders are transparent intermediates and
must be declared in the same visual plan so two text layers never compete.

The per-video directories have strict meanings:

- `raw/` — imported originals, never overwritten;
- `assets/` — video-specific media plus rights information;
- `clips/` — reproducible intermediate video/audio;
- `transcripts/` — transcript and all machine-readable editorial plans;
- `compositions/` — project HyperFrames sources and alpha renders;
- `previews/` — human review artifacts, never finals;
- `renders/` — masters and QC evidence only.

## Where to look

- Current work: ignored `STATE.md` when present.
- Agent operating contract: `AGENTS.md` / `CLAUDE.md`.
- Domain language: `CONTEXT.md`.
- Production workflow: `docs/production-lifecycle.md` and `skills/montage.md`.
- Brand integration: `assets/brand/README.md`.
- Architectural decisions: `docs/adr/`.
