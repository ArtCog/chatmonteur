# Production-correctness rules

Hard-won rules from real talking-head production. They are what make an automated
"one command" draft technically safe to continue editing. Encoded into the tools; documented here so
agents and contributors understand *why*.

## Cutting

- **Never stream-copy (`-c copy`) on a cut.** Stream copy cuts only at keyframes,
  so a cut between keyframes freezes frames for seconds. Always re-encode.
- **Never use `select`/`aselect` filters for cutting** long files — they desync
  audio/video. Use frame-accurate `trim`/`atrim` + `concat` (one pass) or
  `auto-editor` for silence.
- **Normalize to clean CFR before cutting.** Raw footage is often variable frame
  rate with messy timestamps; cutting it directly desyncs audio. Rebuild a CFR
  intermediate first (`normalize`).
- **Cut captions by burning before cutting.** Burn subtitles on the normalized
  video, then cut — each kept frame keeps its caption; removed fillers take their
  captions with them. One transcription pass.

## Silence

- **`auto-editor` is O(n²)** in clip length. Run it per scene/clip, never on a
  merged hour-long file. Let auto-editor render directly (don't parse its output
  and re-cut — that was tested and produced artifacts).

## Audio

- **Loudness normalisation is the LAST audio step**, after every cut
  (`loudnorm`, target ≈ −14 LUFS for YouTube).
- **Verify audio by LEVEL, not track duration.** A track of the correct length
  can be pure silence. Check `mean_volume` (volumedetect); the `render` tool
  warns when output looks silent (< −60 dBFS).
- Prefer clean cuts with micro-fades over crossfades, which clip word endings.

## Encoding

- **Auto-detect the encoder.** Never hardcode `h264_nvenc`. Pick the best
  available: NVENC → QSV → VideoToolbox → libx264. The same pipeline must run on
  a creator's NVIDIA box, a Mac, and a GPU-less CI server.
- Quality-targeted params per encoder (CQ/CRF/global_quality), not bitrate
  guessing. `+faststart` for web playback.

## Workflow

- **Plan before render.** Show the user what will be cut (from `edl.json`) and
  get approval. Offer a fast 720p preview before the full-resolution render.
- **Resume, don't redo.** Checkpoints skip completed steps whose inputs are
  unchanged — saves time and paid API calls.
