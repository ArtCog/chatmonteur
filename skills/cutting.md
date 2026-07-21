# Cutting — pauses, fillers, stumbles

Two tiers. Route first, then follow the matching section exactly.

- **Tier 1 — dumb cut (deterministic):** remove silence/pauses by audio level. No transcript reasoning. auto-editor renders directly.
- **Tier 2 — intelligent cut (LLM):** fillers ("um", "uh"), false starts, repeated takes. You reason over a verbatim word-level transcript, produce a cut-plan, get user approval, then the CLI executes the EDL in one ffmpeg pass.

Never mix tiers in one pass: dumb cut first (it shrinks the transcript workload), intelligent cut second.

---

## Tier 1 — silence removal (THE CANON)

Battle-tested order. Do not improvise: do not lower the threshold for quiet recordings, do not cut raw un-normalized mixes, do not invent values.

### Route by audio tracks (agent does this silently)

1. `ffprobe` the file — how many audio streams?
2. **Two streams that differ** (stream 0 = mix for the viewer, stream 1 = clean voice mic) → **Branch B: cut by the voice track.** Default for multi-track recordings (OBS etc.). Verify the streams actually differ: `-filter_complex "[0:a:0][0:a:1]join=inputs=2:channel_layout=quad,pan=stereo|c0=c0-c2|c1=c1-c3,volumedetect"` — max ≈ −91 dB means identical.
3. **One stream** (or identical streams) → **Branch A: cut by the mix.** Warn the user: noisy pauses survive a mix-based cut.
4. Branch B but the background is *meaningful* audio (someone else's speech, TTS, melodic music) → **ask the user**: cut by voice (background will be chopped mid-word at joins) or by mix (much less gets cut — that is correct)? Non-meaningful noise (UI clicks, game sounds) → Branch B is safe, joins are inaudible.
5. Never bake background music into the recording path — music is added as a continuous layer at final render (see `sound.md`), so it never gets chopped.

### Branch A — single mixed track

```bash
# 0. INPUT CHECK (5 s): if mean_volume is quieter than −24 LUFS, STOP —
#    tell the user their mic gain is too low; do NOT compensate with the threshold
ffmpeg -i RAW -map 0:a:0 -af volumedetect -f null -

# 1. NORMALIZE FIRST — required, protects quiet consonants from being cut.
#    The threshold is relative; on quiet audio 0.14 shreds words into slivers.
#    Same 0.14 on normalized audio behaves correctly. Raise the audio, never lower the threshold.
ffmpeg-normalize RAW -o NORM.mkv -t -14 -tp -1.5 -c:a aac -b:a 256k

# 2. PREVIEW GATE — no render until healthy: median clip ≥1.4 s, ~40 clips per 2–3 min.
#    A piece-count explosion = threshold too high / audio not normalized. Investigate, don't render.
auto-editor NORM.mkv --edit audio:0.14 --margin 0.12s,0.10s --preview

# 3. CUT — whole file, auto-editor renders directly (never parse its output and re-cut)
auto-editor NORM.mkv --edit audio:0.14 --margin 0.12s,0.10s \
  --video-codec h264_nvenc --video-bitrate 10M \
  --audio-bitrate 256k --sample-rate 48000 --no-open -o CLEAN.mp4
# (no NVENC → --video-codec libx264)

# 4. TRUE-PEAK FIX (mandatory after ANY render — see production-rules.md §true-peak)
```

### Branch B — separate voice track (cut by voice, keep the mix)

Detect silence ONLY on the voice stream. Cutting by the mix is wrong: demo/game noise reads as "speech" (measured: mix-based cut removed −8%, voice-based −33% of the same file).

```bash
# B0. verify: 2 audio streams; voice peak ≈ −6±2 dB
#     (threshold is a fraction of the track's PEAK — a stray click shifts the line)
ffprobe -v error -show_entries stream=index,codec_type -of compact RAW.mkv
ffmpeg -i RAW.mkv -map 0:a:1 -af volumedetect -f null -

# B1. PREVIEW required. Feed the RAW file: normalizing a demo-recording before the cut
#     switches the normalizer into dynamic mode and destroys the speech/pause gap.
auto-editor RAW.mkv --edit "audio:threshold=0.06,stream=1" --margin 0.12s,0.10s --preview

# B2. CUT — all tracks are cut in sync by the voice track's decisions
auto-editor RAW.mkv --edit "audio:threshold=0.06,stream=1" --margin 0.12s,0.10s \
  --video-codec h264_nvenc --video-bitrate 10M \
  --audio-bitrate 256k --sample-rate 48000 --no-open -o CUT.mp4

# B3. true-peak fix; the MIX goes into the final. Loudness −14 happens on the final master, NOT here.
ffmpeg -y -i CUT.mp4 -map 0:v:0 -map 0:a:0 -c:v copy \
  -af "alimiter=limit=0.75:level=false:attack=3:release=30" \
  -c:a aac -b:a 384k -ar 48000 -movflags +faststart FINAL.mp4
```

Transcribe from `CUT.mp4` (the clean voice stream is still alive there), not from the flattened final.

### Locked parameters — and why

| Param | Value | Reason |
|---|---|---|
| threshold (normalized mix) | `0.14` | valid ONLY on −14 LUFS-normalized audio |
| threshold (raw voice track) | `0.06` | validated by ear on full videos (0.03 kept breaths; 0.06 cuts breath, keeps words) |
| `--margin` | `0.12s,0.10s` | lead-in 0.12 protects soft word onsets («э», «п»); tail 0.10 kills trailing breath. Tight tail 0.07s only on explicit request |
| `mincut`/`minclip` | defaults | protect short consonant gaps inside words — do not strip |
| `--sample-rate 48000` | forced | auto-editor upsamples to 96 kHz by default → clicks at concat joints |

### Traps

- **auto-editor is O(n²)** in file length: 2 min → ~18 s; 1 hour → hours. Cut per scene before concat whenever scenes exist. Long single file → run in background.
- **Silent-demo trap:** an on-screen demo recorded quietly can sit below threshold even after voice normalization → cut out as "silence" though it is content. Check a region with `ffmpeg -ss S -t D -i f -af volumedetect -f null -` and read **max_volume** (`-ss` after `-i`; loudnorm "Input Integrated" gates quiet audio and lies). Protect a known range in the same call: `--add-in START,STOP`.
- Noise floor sanity: voice-track pause noise should sit ~7–10 dB below the threshold line. If cutting misbehaves, look at mic gain/gate first — never tune the threshold blindly.

---

## Tier 2 — intelligent cut (fillers, false starts, retakes)

Methodology (adapted from video-use, MIT):

0. **Audio pre-pass when the raw file has multi-second silent holes:** run a GENTLE
   auto-editor pass BEFORE transcription (`auto-editor RAW -m 1.0s ... -o depaused`) —
   long dead air makes hosted ASR drift into "audio event" mode and drop word timestamps.
   Then re-encode the depaused file to a clean CFR intermediate before any per-segment
   cutting (auto-editor MKV output has non-monotonic audio timestamps; short-segment seeks
   on it desync audio — see the CFR rule in `production-rules.md`).
1. **Verbatim word-level transcript is mandatory.** Never phrase/SRT mode (loses sub-second gaps), never normalized fillers (loses the editorial signal). If the local transcriber smoothed out fillers, tell the user what that costs and offer the hosted-ASR upgrade.
2. **You reason, no detector script does.** Read the transcript; tag fillers, false starts, repeated sentences, dead segues at decision time. Filler vocab seed (extend per language): en `um, uh, uhm, erm, like, literally`; ru `эээ, ммм, эм, ну, типа, вот, значит, короче`.
3. **Cut points = word boundaries + pad.** Never inside a word. Padding by cut type (battle-tested):

   | Cut type | Tail (after kept word) | Lead (before next word) |
   |---|---|---|
   | Mid-sentence (comma) | 100 ms | 80 ms |
   | Sentence boundary (period) | 200 ms | 130–150 ms |
   | Video start | — | 130–150 ms |
   | Video end | 600–700 ms | — |

   Video-end trap: full-context ASR often marks the last word's end 1–2 s late. Verify
   two-step — re-transcribe an isolated slice around the ending and take the TRUE word-end.
   Record the padding used in the EDL (`_padding_params` block) — no magic numbers.
4. **Produce a cut-plan and STOP for approval.** List every removal: timestamp, quoted text, reason. ASR mishears brands and technical terms as stumbles («Claude Code» → "код-код") — the user catches these, you don't. Never auto-apply.
5. **Execute via the CLI EDL engine** (single ffmpeg `trim`/`atrim`+`concat` pass, frame-accurate). Never stream-copy, never select-filters, never hand-written cut scripts (см. production-rules.md).
6. **Verify by level, not by duration:** a cut audio track of the right length can still be silence. `volumedetect` → mean_volume sane, then spot-check 2–3 joins.
