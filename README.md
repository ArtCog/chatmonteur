# ChatMonteur — AI video editor for talking-head footage

> Does the work of an experienced video editor — meaning-based cutting, captions, graphics,
> sound — driven by your coding agent (Claude Code / Codex), not a timeline.

**ChatMonteur** (*monteur* — French/Russian for "film editor") is an extensible,
agent-orchestrated editing studio for **real talking-head recordings** (vlogs, tutorials,
explainers). You drop in raw footage, say what you want in plain language, and the agent
runs a battle-tested pipeline: transcribe → cut pauses & stumbles by meaning → subtitles →
motion graphics → sound → color → render. It edits recordings; it does not generate video
from scratch.

It does **not** reinvent the engines. It orchestrates the best open tools —
[video-use](https://github.com/browser-use/video-use),
[hyperframes](https://github.com/heygen-com/hyperframes),
[auto-editor](https://github.com/WyattBlue/auto-editor),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), ffmpeg — and adds the two
parts that are actually hard:

1. **An editorial brain** — [`skills/`](skills/INDEX.md): the decision knowledge of a
   working YouTube editor (where to cut, how to pad cuts, when to zoom, how loud the music
   bed sits, what never to do), written for agents to follow.
2. **Hard-won correctness rules** — so a single command doesn't produce a broken video
   (no frozen frames, no A/V desync, no crushed audio).

> 🚧 **Status: v0.1, building in the open.** The core pipeline works end-to-end
> (raw → finished video in one command); currently being hardened by editing a real
> YouTube channel's videos with it, start to finish.

## Quick start

```bash
git clone https://github.com/ArtCog/chatmonteur && cd chatmonteur
./setup.sh                  # Windows: ./setup.ps1   (installs chatmonteur + free local toolchain)
chatmonteur tools           # see capabilities and what's ready
chatmonteur edit raw.mp4    # raw footage → projects/raw/renders/final.mp4
```

Then just talk to your agent: *"edit raw.mp4 — cut the filler, add captions,
warm look."* It runs the pipeline, shows you a cut-plan, renders a preview, and
finalises.

## Why ChatMonteur

- **One command, not copy-paste.** A real CLI + agent orchestration, instead of pasting prompts into an IDE.
- **Talking-head depth.** Cut by meaning, kill filler, fix stumbles, sync captions and graphics to words.
- **An editor's judgment, encoded.** The `skills/` knowledge base came from real published videos, not from a prompt-engineering session.
- **Free by default.** Local `faster-whisper` out of the box — no paid API key required. Premium engines (ElevenLabs Scribe) are an opt-in upgrade.
- **Cross-platform encode.** NVENC when available, graceful fallback to libx264 / VideoToolbox / QSV.
- **Built to grow.** A plugin/tool registry — new tools and pipelines drop in without touching the core.

## How it works (talking-head pipeline)

```
raw footage
  → normalize (clean CFR, −14 LUFS)  don't desync on VFR input; level-control the audio
  → cut pauses (audio level)         auto-editor, locked thresholds — blind to meaning, safe
  → transcribe (word-level)          faster-whisper (local) / ElevenLabs (opt-in)
  → subtitles
  → color (LUT)
  → render                           correctness-checked output

agent-driven on top (never automatic):
  → intelligent cut                  the AGENT reasons over the transcript, writes an
    (fillers, stumbles, retakes)     EDL cut-plan, you approve → one frame-accurate pass
  → motion graphics                  hyperframes compositions authored by the agent
  → sound (music bed, ducking, SFX)
```

The decision layer behind every step lives in [`skills/`](skills/INDEX.md) — readable,
auditable, and usable directly by Claude Code / Codex / Cursor.

## Status & roadmap

v0.1 ships a working talking-head pipeline behind one command. Growth (shorts, podcast,
B-roll, diarization, denoise, background replacement) lands as plugins.

## Credits & license

Built on the shoulders of open-source tools — see [CREDITS.md](CREDITS.md). Architecture ideas (tool registry, checkpoints) inspired by [OpenMontage](https://github.com/calesthio/OpenMontage); no code copied.

MIT © 2026 [ArtCog](https://github.com/ArtCog). The bundled engines keep their own licenses.

🇷🇺 [Русская версия — README.ru.md](README.ru.md)
