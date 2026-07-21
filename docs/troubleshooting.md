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

**Captions drift after cutting**
chatmonteur burns captions *before* cutting so kept frames keep their captions. If
you reorder steps, keep that order or re-transcribe the cut video.

**Everything got removed by `cut_meaning`**
Thresholds too aggressive or a bad transcript. Raise `pause_max`, check the
`transcripts/edl.json`, or pass a custom `fillers` list.
