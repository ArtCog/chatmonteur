# AGENTS.md — chatmonteur for coding agents (Codex et al.)

chatmonteur is an agent-driven talking-head video editor. You orchestrate it; the
heavy lifting is real tools (ffmpeg, faster-whisper, auto-editor, hyperframes).

**Mission: the most capable open-source autonomous video editor in the world** — MIT,
free-by-default, quality gates that can refuse a weak edit. First user: Артур's YouTube
channel «ИИмерсивный» (dogfood on real footage decides what counts as done). Road:
brand-book port → dogfood → v0.1 release → applications to Claude for Open Source and
Codex for Open Source. **Living state: `PLAN.local.md`, latest checkpoint — read it at
session start.** The conversation is not the project's memory; the files are.

This file mirrors `CLAUDE.md` — read that for the full contract. Essentials:

## Run it

```
chatmonteur edit <raw.mp4> [--lut warm_film] [--project name] [--model large-v3]
chatmonteur tools     # list capabilities + readiness
```

Pipeline `talking_head` (mechanical only): normalize (CFR + level prep) →
cut pauses by audio level → transcribe → subtitles → color → render.
Output: `projects/<name>/renders/final.mp4`. Re-runs resume from checkpoints.

The INTELLIGENT cut (fillers/false starts/retakes) is the agent's reasoning,
not a pipeline step: read `transcripts/master.json`, write `transcripts/edl.json`,
show the cut-plan, wait for approval, then run the `cut_edl` capability and
re-run color/render. See `skills/cutting.md` Tier 2.

## Always

- **Start any edit session from `skills/montage.md`** — it routes mechanical vs
  editorial work and lists the approval gates. `skills/INDEX.md` is the map of
  the whole editorial knowledge base.
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
