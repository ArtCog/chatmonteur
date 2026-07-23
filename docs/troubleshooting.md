# Troubleshooting

**`chatmonteur tools` shows `missing: binary:ffmpeg`**
Install ffmpeg and ensure it's on PATH. Windows: `winget install Gyan.FFmpeg`.
macOS: `brew install ffmpeg`. Linux: `apt install ffmpeg`.

**`missing: python:faster_whisper`**
`pip install chatmonteur[whisper]` (or re-run `setup`). First transcription
downloads the model (large-v3 ≈ 3 GB; use `--model small` to start light).

**Transcription is slow / no GPU**
The tool falls back to CPU automatically. Use a smaller model (`--model small`)
or a paid backend. GPU needs CUDA + the matching `ctranslate2`/torch build.

**Output video looks frozen in places**
Something stream-copied a cut. chatmonteur never does this; if you added a custom
tool, always re-encode — never `-c copy` on a cut.

**Audio is silent in the final**
Check `mean_volume` — the `render` tool warns below −60 dBFS. Usually a wrong
audio map upstream. Verify by *level*, not track duration.

**Subtitles/LUT filter fails on Windows with a path error**
That's the drive-colon problem; chatmonteur runs ffmpeg from the file's folder to
avoid it. If you wrote a custom tool, do the same (`cwd=` + bare filename).

**Captions drift after an agent-driven meaning cut**
Captions are burned before `cut_edl` runs, so kept frames keep their captions.
If you cut a video whose captions were made from a DIFFERENT timeline,
re-transcribe first — timings drift after every cut.

**The pause cut removed too much / shredded words**
`cut_silence`'s threshold (0.14) is a fraction of peak and is only valid on
loudness-normalised audio — the default `normalize` step does that. If you fed
it raw quiet audio, normalize first (never lower the threshold). A silent
screen-demo can also sit under the threshold: check the preview and protect
the range (see skills/cutting.md, "silent-demo trap").

**`cut_edl` refused to run or output looks wrong**
The EDL is authored by the agent, not detected by a script. Check
`transcripts/edl.json` ranges against the transcript, and remember the
cut-plan must be approved before executing (skills/cutting.md Tier 2).
