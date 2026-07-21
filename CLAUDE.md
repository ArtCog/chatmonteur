# CLAUDE.md — driving chatmonteur

You (the agent) are the control plane for **chatmonteur**: an extensible talking-head
video editor. A creator points you at raw footage and describes what they want;
you run the pipeline and iterate. Default language with the user: theirs.

## The one command

```
chatmonteur edit <raw.mp4> [--lut warm_film] [--project name] [--model large-v3]
```

This runs the **talking_head** pipeline: normalize → transcribe → subtitles →
cut (fillers + pauses) → color → render. Output lands in
`projects/<name>/renders/final.mp4`. Re-running resumes from checkpoints.

For fine control, run capabilities individually via the registry (see
`docs/extending.md`) instead of the whole pipeline.

## The editorial brain: skills/

The CLI is the hands; **`skills/` is the head.** At the start of any edit
session read `skills/montage.md` (the orchestrator — routes mechanical vs
editorial work, defines the ①skeleton→②edit→③final pipeline and the approval
gates). `skills/INDEX.md` maps the rest: cutting (two-tier), subtitles, motion,
hook editing, sound, plus `skills/references/` loaded on demand. When the
skills and this file disagree on editing procedure, the skills win.

## Cut-plan discipline (IMPORTANT)

Before a heavy final render, **show the user the plan and get approval**:
- After `cut_meaning`, read `projects/<name>/transcripts/edl.json` and summarise
  in plain language what will be removed (fillers, pauses, ranges, kept seconds).
- Offer a fast preview (`render … preview=True`, 720p libx264) before the full
  1440p render. Cheap iteration beats re-rendering 20 minutes.

## Production-correctness rules (never break these)

These are why "one command" doesn't produce a broken video. Full detail in
`skills/production-rules.md`.

1. **Never `-c copy` on a cut** — always re-encode (frozen frames otherwise).
2. **Normalize first** — VFR/odd input must become clean CFR before cutting,
   or audio desyncs.
3. **Loudness last** — `loudnorm` is the final audio step, after all cuts.
4. **Verify audio by LEVEL, not duration** — a full-length track can be silent;
   check `mean_volume` (the render tool warns if output looks silent).
5. **Silence removal is O(n²)** — run `cut_silence` per scene/clip, not on a
   merged 1-hour file.
6. **Encoder is auto-detected** — never hardcode `h264_nvenc`; the tools pick
   NVENC/QSV/VideoToolbox/libx264 per machine.

## Where things live

```
projects/<name>/
  clips/         normalized, cut, graded intermediates
  transcripts/   master.json, captions.srt, edl.json
  previews/      fast proxy renders
  renders/       final.mp4  (the only "output")
  .chatmonteur/      checkpoint.json (resume state)
```
Never write to `raw/` or the repo root. Finals go only to `renders/`.

## Free by default

Default transcription is local `faster-whisper` (no API key). Paid backends
(ElevenLabs) are opt-in. Tell the user before invoking any `cost: paid` tool.

## Extending

New capability = new module in `chatmonteur/tools/` exposing `TOOL`. New flow = a
YAML in `pipelines/`. See `docs/extending.md`.
