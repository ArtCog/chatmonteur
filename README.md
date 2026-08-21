# ChatMonteur — AI video editor for talking-head footage

> Does the work of an experienced video editor — meaning-based cutting, captions, graphics,
> sound — driven by your coding agent (Claude Code / Codex), not a timeline.

**ChatMonteur** (*monteur* — French/Russian for "film editor") is an extensible,
agent-orchestrated editing studio for **real talking-head recordings** (vlogs, tutorials,
explainers). You drop in raw footage, say what you want in plain language, and the agent
runs a battle-tested pipeline: transcribe → cut pauses & stumbles by meaning → subtitles →
motion graphics → sound → color → render. It edits recordings; it does not generate video
from scratch.

It does **not** reinvent the engines. It orchestrates proven open tools —
[hyperframes](https://github.com/heygen-com/hyperframes),
[auto-editor](https://github.com/WyattBlue/auto-editor),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), and ffmpeg — while adapting
the agent-led meaning-cut video-use methodology from
[video-use](https://github.com/browser-use/video-use). It adds the three
parts that are actually hard:

1. **An editorial brain** — [`skills/`](skills/INDEX.md): the decision knowledge of a
   working YouTube editor (where to cut, how to pad cuts, when to zoom, how loud the music
   bed sits, what never to do), written for agents to follow.
2. **Hard-won correctness rules** — so a single command doesn't produce a broken video
   (no frozen frames, no A/V desync, no crushed audio).
3. **Two gates that say no** — the part that actually keeps quality up, below.

The exact ownership boundary — what ChatMonteur builds and what it delegates to
auto-editor, faster-whisper, the Video-Use methodology, HyperFrames, and ffmpeg — is recorded in
the [architecture map](docs/architecture.md). In particular, HyperFrames owns
visual brand and motion rendering; ChatMonteur owns editorial selection and the
end-to-end verified workflow.

## The two gates

An agent that can only say yes will hand you a weak edit with total confidence. So two
checks are allowed to refuse, and neither is a log warning you can scroll past:

- **The plan gate.** Before a single frame is burned, the visual plan is scored and rejected
  if it will read as "he just cut the pauses": a stretch over 90 s with no visual event, text
  on screen more than 60 % of the runtime, repeated captions, three identical zooms in a row.
- **The file gate.** Every encoded artifact is re-opened as a stranger would open it — frames
  sampled at 10/35/65/90 % (not the head and tail, where black is by design), audio checked
  by level for silence and clipping, runtime compared against what the encoder was handed.
  Anything broken stops delivery and leaves a sibling `.qc.json` report as the evidence.
  A healthy mechanical draft says `continue_editing`; an internal master with
  unresolved media rights says `review_rights`; only a cleared master says `ship`.

Both were built after real failures, and both are unit-tested rule sets rather than
heuristics buried in a prompt.

> **Status: v0.1.** The mechanical pipeline works end-to-end
> behind one command; the complete agent-driven workflow has now survived a real
> YouTube-channel edit from restored raw footage to a checked master.

## Quick start

The supported v0.1 distribution is the repository checkout because the
agent-facing editorial knowledge in `skills/` is part of the product, not just
Python package data.

```bash
git clone https://github.com/ArtCog/chatmonteur && cd chatmonteur
./setup.sh                  # Windows: ./setup.ps1   (installs chatmonteur + free local toolchain)
chatmonteur tools           # see capabilities and what's ready
chatmonteur init 2026-demo --title "My video"       # optional explicit project creation
chatmonteur edit raw.mp4 --project 2026-demo        # imports raw → projects/2026-demo/raw/
                                                    # draft → projects/2026-demo/renders/mechanical-draft.mp4
chatmonteur run sound --project 2026-demo --params examples/sound-run.json
                                                    # execute any listed capability from JSON
```

The command deliberately stops at a technically valid **mechanical draft**. Then
talk to your agent: *"finish this edit — cut the filler, add captions, graphics,
and sound."* It shows the required approval gates and promotes only the completed
edit to a master.

`talking_head` accepts a single audio stream. For an OBS file with separate mix
and microphone tracks it refuses to guess and points the agent to the documented
Branch B workflow in `skills/cutting.md`.

## Why ChatMonteur

- **It can refuse.** A weak plan and a broken file are both stopped by a tested rule set, not flagged in a log.
- **One command, not copy-paste.** A real CLI + agent orchestration, instead of pasting prompts into an IDE.
- **Talking-head depth.** Cut by meaning, kill filler, fix stumbles, sync captions and graphics to words.
- **An editor's judgment, encoded.** The `skills/` knowledge base came from real published videos, not from a prompt-engineering session.
- **Numbers, not vibes.** Every threshold in [`engineering-facts.md`](skills/references/engineering-facts.md) is written down with why it holds and where it lives in the code.
- **Free by default.** Local `faster-whisper` out of the box — no paid API key required. Additional transcription backends can be added as tools when their adapters exist.
- **Cross-platform encode.** NVENC when available, graceful fallback to libx264 / VideoToolbox / QSV.
- **Built to grow.** A plugin/tool registry — new tools and pipelines drop in without touching the core.

## How it works (talking-head pipeline)

```
raw footage
  → normalize (clean CFR, linear gain) don't desync on VFR input; prepare audio for cutting
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
                                     voice by roughly 2–6 dB, notched in the speech band
```

The decision layer behind every step lives in [`skills/`](skills/INDEX.md) — readable,
auditable, and usable directly by Claude Code / Codex / Cursor.

## Status & roadmap

v0.1 ships a working mechanical front door plus the agent-driven finishing workflow.
Growth (shorts, podcast, diarization, denoise, auto-reframe) lands as plugins — a new
capability is one module in `chatmonteur/tools/`, see [docs/extending.md](docs/extending.md).

## Contributing

Bug reports, documentation fixes, and focused pull requests are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md); report suspected vulnerabilities privately
through [SECURITY.md](SECURITY.md).

## Credits & license

Built on the shoulders of open-source tools — see [CREDITS.md](CREDITS.md). Architecture ideas (tool registry, checkpoints) inspired by [OpenMontage](https://github.com/calesthio/OpenMontage); no code copied.

MIT © 2026 [ArtCog](https://github.com/ArtCog). The bundled engines keep their own licenses.

🇷🇺 [Русская версия — README.ru.md](README.ru.md)
