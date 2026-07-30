# CLAUDE.md — driving chatmonteur

You (the agent) are the control plane for **chatmonteur**: an extensible talking-head
video editor. A creator points you at raw footage and describes what they want;
you run the pipeline and iterate. Default language with the user: theirs.

## The one command

```
chatmonteur edit <raw.mp4> [--lut warm_film] [--project name] [--model large-v3]
```

This runs the **talking_head** pipeline — mechanical steps only: normalize
(CFR + loudnorm −14) → cut pauses by audio level → transcribe → color
(optional; DEFAULT IS UNGRADED — a LUT only when the user picks one) →
subtitles → render. Output lands in `projects/<name>/renders/final.mp4`.
Re-running resumes from checkpoints. Before burning subtitles, ASK which of
the five brand variants fits this video (`skills/subtitles.md`).

For fine control, run capabilities individually via the registry (see
`docs/extending.md`) instead of the whole pipeline.

## The editorial brain: skills/

The CLI is the hands; **`skills/` is the head.** At the start of any edit
session read `skills/montage.md` (the orchestrator — routes mechanical vs
editorial work, defines the ①skeleton→②edit→③final pipeline and the approval
gates). `skills/INDEX.md` maps the rest: cutting (two-tier), subtitles, motion,
hook editing, sound, plus `skills/references/` loaded on demand. When the
skills and this file disagree on editing procedure, the skills win.

## Phase ③ — the visual pass is YOUR plan, one artifact (IMPORTANT)

After the meaning cut locks timing, plan the WHOLE visual pass as
`projects/<name>/transcripts/storyboard.json` — sections `zooms`, `overlays`,
`inserts` (formats in `skills/motion.md`). Show the storyboard, STOP for
approval, then call the `storyboard` capability ONCE — it burns the sections in
the load-bearing order (zooms → overlays → inserts) and hands one video
downstream to color/subtitles/render.

## The intelligent cut is YOUR job, not a script's (IMPORTANT)

Fillers, false starts, retakes: no tool auto-decides these. Per
`skills/cutting.md` Tier 2 (video-use methodology), YOU:

1. Read the word-level transcript (`projects/<name>/transcripts/master.json`).
2. Tag fillers/stumbles/retakes at decision time, reasoning by meaning — ASR
   mishears brands, so never trust the words blindly.
3. Write the plan as `projects/<name>/transcripts/edl.json`
   (`{"removed": [[a,b], …]}`), and **show the user a plain-language cut-plan
   (timestamp, quoted text, reason). STOP for approval.**
4. Only after approval: run the `cut_edl` capability (single frame-accurate
   ffmpeg pass), then re-run color/render on the result.
5. Offer a fast preview (`render … preview=True`, 720p) before the full 1440p
   render. Cheap iteration beats re-rendering 20 minutes.

## Two gates decide quality — and both can say NO (IMPORTANT)

Approval gates ask the user; these two ask the work itself, and refuse.

1. **The plan gate** — `storyboard` scores your visual plan before burning a single
   frame and rejects one that will read as "he just cut the pauses": a stretch over
   90 s with no visual event, text on screen more than 60 % of the time, repeated
   captions, three identical zooms in a row. Fix the plan; only pass
   `allow_thin=True` when plain footage is genuinely the right answer.
2. **The file gate** — `qc` is the last pipeline step and blocks delivery of a
   broken render: black frames sampled at 10/35/65/90 %, a silent or clipped audio
   track, missing streams, or a runtime that drifted more than 25 % from what the
   encoder was handed. Evidence lands in `renders/final.qc.json`.

When either fires, **never** work around it by re-running with the check disabled.
Fix what it names. That is the whole point of it existing.

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
