# Credits

chatmonteur is glue + opinionated correctness rules on top of excellent open-source work.
It **depends on** these tools (installed by setup, not vendored) and keeps their licenses intact.

## Bundled engines (dependencies)

| Tool | What it does in chatmonteur | License | Project |
|---|---|---|---|
| **video-use** | cut by meaning, filler/stumble removal, color | MIT | https://github.com/browser-use/video-use |
| **hyperframes** | motion graphics & captions (HTML → MP4) | Apache-2.0 | https://github.com/heygen-com/hyperframes |
| **auto-editor** | silence / dead-space removal (per scene) | MIT | https://github.com/WyattBlue/auto-editor |
| **faster-whisper** | local word-level transcription (default) | MIT | https://github.com/SYSTRAN/faster-whisper |
| **ffmpeg** | encode / filter / mux | LGPL/GPL | https://ffmpeg.org |
| **yt-dlp** | optional source download | Unlicense | https://github.com/yt-dlp/yt-dlp |

Optional / growth plugins (added later) will be credited here as they land.

## Inspiration

Architecture ideas — tool registry, provider selectors, JSON checkpoints — were learned from
**OpenMontage** (https://github.com/calesthio/OpenMontage, AGPL-3.0). **No code was copied**; chatmonteur
is an independent MIT implementation.

## Author

Built by [ArtCog](https://github.com/ArtCog). The hard-won ffmpeg/cutting correctness rules come from
real production use on a YouTube channel.
