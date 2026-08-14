# AGENTS.md — chatmonteur for coding agents (Codex et al.)

chatmonteur is an agent-driven talking-head video editor. You orchestrate it; the
heavy lifting is real tools (ffmpeg, faster-whisper, auto-editor, hyperframes).

**Mission: the most capable open-source autonomous video editor in the world** — MIT,
free-by-default, quality gates that can refuse a weak edit. First user: Артур's YouTube
channel «ИИмерсивный» (dogfood on real footage decides what counts as done). Road:
real-media dogfood → v0.1 release → applications to Claude for Open Source and
Codex for Open Source. A maintainer checkout may contain ignored `STATE.md` and
`PLAN.local.md`; read them first when present. A fresh public clone starts from
this file, `README.md`, `docs/architecture.md`, and `docs/production-lifecycle.md`.

## Architecture boundary

Read `docs/architecture.md` before changing ownership between ChatMonteur and an
external engine. HyperFrames owns visual brand through native `frame.md` and its
registry; ChatMonteur owns editorial intent, component selection, source policy,
workflow state, approval gates, compositing, and QC. Do not recreate an external
engine's supported system inside ChatMonteur.

This file mirrors `CLAUDE.md` — read that for the full contract. Essentials:

## Mandatory per-video container

Before any edit, identify `projects/<yyyy-slug>/PLAN.md` and read it. If the
project does not exist, run `chatmonteur init <yyyy-slug> --title "..."` or use
`chatmonteur edit ... --project <yyyy-slug>`; `edit` initializes the same full
contract and imports the source into immutable `raw/` automatically. Never keep
an active video's working state in `_audit/`, `черновик/`, or chat history.

The public montage layout is `raw/`, `assets/`, `clips/`, `transcripts/`,
`compositions/`, `previews/`, and `renders/`.
Approval artifacts live in `previews/`; only masters and QC evidence live in
`renders/`.

Artur's private preproduction workflow (`preproduction/`, research, Russian
spoken-script adaptation, and `youtube/` packaging) may wrap the same project,
but is not part of the public ChatMonteur v0.1 contract. The handoff into the
public core is source media plus language-neutral transcript/EDL/storyboard data.

## Channel CTA identity

For the default «ИИмерсивный» brand, read `assets/brand/default/channel.json`
before adding any YouTube or Telegram CTA. The Telegram channel is encoded there
once and reusable QR assets are generated from it by `build_catalog.py`.
`@Art_Cog` is Artur's personal account: never put it on screen as a channel
handle, CTA, link, or QR destination. Do not reconstruct channel addresses from
memory or from an older composition.

## Run it

```
chatmonteur init <yyyy-slug> --title "Video title"
chatmonteur edit <raw.mp4> [--lut warm_film] [--project yyyy-slug] [--model large-v3]
chatmonteur tools     # list capabilities + readiness
chatmonteur run <capability> --project <yyyy-slug> --params <run.json>
```

Pipeline `talking_head` (mechanical only): normalize (CFR + level prep) →
cut pauses by audio level → transcribe → subtitles → color → render.
Output: `projects/<name>/renders/mechanical-draft.mp4`. A passing draft continues
to the editorial/visual/sound gates; it is not a master. Re-runs resume from checkpoints.
The front door refuses multi-audio OBS sources rather than guessing a track; route
those through Branch B in `skills/cutting.md`, then resume with `chatmonteur run`.

The INTELLIGENT cut (fillers/false starts/retakes) is the agent's reasoning,
not a pipeline step: read `transcripts/master.json`, write `transcripts/edl.json`,
show the cut-plan, wait for approval, then run the `cut_edl` capability and
re-run color/render. Execute individual capabilities through `chatmonteur run`
with a JSON parameter object. See `skills/cutting.md` Tier 2.

## Always

- **Start any edit session from `skills/montage.md`** — it routes mechanical vs
  editorial work and lists the approval gates. `skills/INDEX.md` is the map of
  the whole editorial knowledge base.
- **Before selecting any motion graphic, read
  `assets/brand/default/SELECTION-GUIDE.md`.** Then query the generated
  `catalog.json` by `card.editorial.role`; never choose from memory or by card
  number alone. `usage-profiles.json` is the selection authority for all 68 cards.
- **Show a cut-plan before the final render** (read `transcripts/edl.json`,
  summarise removals) and offer a 720p preview first.
- Follow the **production-correctness rules** in `skills/production-rules.md`
  (never `-c copy`; normalize→CFR first; loudnorm last; verify audio by level;
  silence removal per-scene; encoder auto-detected).
- Default to **free/local** transcription; warn before any paid tool.
- Write only under `projects/<name>/`; finals only in `renders/`.

## Extend

Add a capability: new module in `chatmonteur/tools/` exposing a `TOOL` instance.
Add a flow: a YAML in `pipelines/`. See `docs/extending.md`.
