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
3. **Two gates that say no** — the part that actually keeps quality up, below.

## The two gates

An agent that can only say yes will hand you a weak edit with total confidence. So two
checks are allowed to refuse, and neither is a log warning you can scroll past:

- **The plan gate.** Before a single frame is burned, the visual plan is scored and rejected
  if it will read as "he just cut the pauses": a stretch over 90 s with no visual event, text
  on screen more than 60 % of the runtime, repeated captions, three identical zooms in a row.
- **The file gate.** The finished render is re-opened as a stranger would open it — frames
  sampled at 10/35/65/90 % (not the head and tail, where black is by design), audio checked
  by level for silence and clipping, runtime compared against what the encoder was handed.
  Anything broken stops delivery and leaves `renders/final.qc.json` as the evidence.

Both were built after real failures, and both are unit-tested rule sets rather than
heuristics buried in a prompt.

> 🚧 **Status: v0.1, building in the open.** The core pipeline works end-to-end
> (raw → finished video in one command); currently being hardened by editing a real
> YouTube channel's videos with it, start to finish.

## Quick start

```bash
git clone https://github.com/ArtCog/chatmonteur && cd chatmonteur
./setup.sh                  # Windows: ./setup.ps1   (installs chatmonteur + free local toolchain)
chatmonteur tools           # see capabilities and what's ready
chatmonteur init 2026-demo --title "My video"       # optional explicit project creation
chatmonteur edit raw.mp4 --project 2026-demo        # imports raw → projects/2026-demo/raw/
                                                    # final → projects/2026-demo/renders/final.mp4
```

Then just talk to your agent: *"edit raw.mp4 — cut the filler, add captions,
warm look."* It runs the pipeline, shows you a cut-plan, renders a preview, and
finalises.

## Why ChatMonteur

- **It can refuse.** A weak plan and a broken file are both stopped by a tested rule set, not flagged in a log.
- **One command, not copy-paste.** A real CLI + agent orchestration, instead of pasting prompts into an IDE.
- **Talking-head depth.** Cut by meaning, kill filler, fix stumbles, sync captions and graphics to words.
- **An editor's judgment, encoded.** The `skills/` knowledge base came from real published videos, not from a prompt-engineering session.
- **Numbers, not vibes.** Every threshold in [`engineering-facts.md`](skills/references/engineering-facts.md) is written down with why it holds and where it lives in the code.
- **Free by default.** Local `faster-whisper` out of the box — no paid API key required. Premium engines (ElevenLabs Scribe) are an opt-in upgrade.
- **Cross-platform encode.** NVENC when available, graceful fallback to libx264 / VideoToolbox / QSV.
- **Built to grow.** A plugin/tool registry — new tools and pipelines drop in without touching the core.

## How it works (talking-head pipeline)

```
raw footage
  → normalize (clean CFR, −14 LUFS)  don't desync on VFR input; level-control the audio
  → cut pauses (audio level)         auto-editor, threshold relative to peak, not absolute
  → transcribe (word-level)          faster-whisper, brand-term dictionary, hallucinations
                                     dropped by the model's own no-speech confidence
  → color (LUT, optional)
  → subtitles                        pauses in the speech decide where a line breaks
  → render
  → qc                               BLOCKS a broken file — black frames, silence, clipping,
                                     duration drift
agent-driven on top (never automatic):
  → intelligent cut                  the AGENT reasons over the transcript, writes an
    (fillers, stumbles, retakes)     EDL cut-plan, you approve → one frame-accurate pass
  → privacy redaction                timecoded solid coverage for credentials/private UI;
                                     inspected before any review copy leaves the project
  → storyboard                       zooms + b-roll + meaning-inserts as ONE approved plan,
                                     scored for boringness before it burns
  → motion graphics                  HyperFrames rendered to transparent ProRes and
                                     composited on the video's own timebase
  → transitions                      cut / crossfade / fade, with one primary kind enforced
                                     across ≥60 % of joins
  → sound                            music bed ducked by sidechain compression under the
                                     voice (measured 8.1 dB), notched in the speech band
```

The decision layer behind every step lives in [`skills/`](skills/INDEX.md) — readable,
auditable, and usable directly by Claude Code / Codex / Cursor.

## Status & roadmap

v0.1 ships a working talking-head pipeline behind one command, 16 capabilities and 87 tests.
Growth (shorts, podcast, diarization, denoise, auto-reframe) lands as plugins — a new
capability is one module in `chatmonteur/tools/`, see [docs/extending.md](docs/extending.md).

## Credits & license

Built on the shoulders of open-source tools — see [CREDITS.md](CREDITS.md). Architecture ideas (tool registry, checkpoints) inspired by [OpenMontage](https://github.com/calesthio/OpenMontage); no code copied.

MIT © 2026 [ArtCog](https://github.com/ArtCog). The bundled engines keep their own licenses.

🇷🇺 [Русская версия — README.ru.md](README.ru.md)
