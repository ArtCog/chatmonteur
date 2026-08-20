# Credits

chatmonteur is glue + opinionated correctness rules on top of excellent open-source work.
Runtime engines are installed by setup, invoked on demand, or documented as system
prerequisites; none are vendored. Their own licenses remain intact.

## Bundled engines (dependencies)

| Tool | What it does in chatmonteur | License | Project |
|---|---|---|---|
| **hyperframes** | motion graphics & captions (HTML → MP4) | Apache-2.0 | https://github.com/heygen-com/hyperframes |
| **auto-editor** | silence / dead-space removal (per scene) | MIT | https://github.com/WyattBlue/auto-editor |
| **faster-whisper** | local word-level transcription (default) | MIT | https://github.com/SYSTRAN/faster-whisper |
| **ffmpeg** | encode / filter / mux | LGPL/GPL | https://ffmpeg.org |

Optional / growth plugins (added later) will be credited here as they land.

## Bundled CC0 sound assets

The publication-safe fallback in `assets/sound/` is redistributed under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Its
machine-readable source of truth is `assets/sound/ledger.jsonl`.

| Asset | Creator | Primary source |
|---|---|---|
| Simple menu/background music loop | polosik | https://opengameart.org/content/simple-menubackground-music-loop |
| Hover (from Dark Sci-Fi Audio Pack) | SRG774 | https://opengameart.org/content/dark-sci-fi-audio-pack |

## Inspiration

| Project | What ChatMonteur learned from it | License | Project |
|---|---|---|---|
| **video-use** | editorial methodology for agent-led meaning cuts; not a runtime dependency | MIT | https://github.com/browser-use/video-use |

Architecture ideas — tool registry, provider selectors, JSON checkpoints — were learned from
**OpenMontage** (https://github.com/calesthio/OpenMontage, AGPL-3.0). **No code was copied**; chatmonteur
is an independent MIT implementation.

## Author

Built by [ArtCog](https://github.com/ArtCog). The hard-won ffmpeg/cutting correctness rules come from
real production use on a YouTube channel.
