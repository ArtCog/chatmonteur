# Known Issues & Anti-Patterns

Loaded on demand. The non-negotiable "never do this" list. Core rules in `production-rules.md`.

## FATAL — will cause visible problems

1. **`-c copy` for cuts** → frozen frames (keyframe issue). ALWAYS re-encode.
2. **select/aselect filters** → audio/video desync on long files. NEVER use; the EDL engine
   uses `trim`/`atrim` + `concat` instead.
3. **Hand-written cut scripts** → desync, missed pauses, garbage. Use auto-editor (Tier 1)
   or the EDL engine (Tier 2). See `../cutting.md`.
4. **`afftdn` noise reduction** → "barrel"/underwater sound on clean recordings. Don't use.
5. **Compressor for loudness normalization** → pumps noise between words. Use two-pass
   `ffmpeg-normalize` (or one-pass `loudnorm`) instead.
6. **Piping long renders through `| tail -N`** → hides progress, looks frozen. Run long
   commands in the background and poll the log.
7. **Mixing fps in concat** (30fps + 60fps with `-c copy`) → duplicate/frozen frames.
   Re-encode to a uniform format first.
8. **xfade without `-pix_fmt yuv420p`** → emits yuv444p; Windows Media Player fails with
   error 0x80004005. Always add the pix_fmt flag.

## WARNINGS

9. **Cascading AAC degradation:** each AAC encode→decode cycle loses quality irreversibly;
   raising bitrate later does not recover it. Don't re-encode AAC more than ~2 times;
   256k is the practical ceiling for speech. Ideal chain: extract WAV → process in WAV →
   encode AAC once at the final step.
10. **Whisper large-v3 is ~3 GB** — downloads on first run, cached under
    `~/.cache/huggingface/hub/`. GPU transcription needs a matching CUDA runtime
    (`cublas64_12.dll` → CUDA 12.x on Windows).
11. **Windows mic auto-gain** gradually changes recording volume mid-take → disable in
    Sound settings (input device properties). Also set Communications → "Do nothing"
    (Communication Mode silently reduces mic volume).
12. **Git Bash on Windows:** `grep -P` (Perl regex) is unsupported — parse with `sed` or
    Python. Very long inline Python commands can die with exit 127 — write a script file.
