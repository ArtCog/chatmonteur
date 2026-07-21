# Multi-Scene Assembly Pipeline

Loaded on demand. Read when assembling a full video from multiple recorded scenes
(trim → normalize → silence-removal → concat → final render). Hard rules in
`production-rules.md` always apply.

## Terminology

- **Scene** = one finished unit (one topic segment of the final video).
- **Multi-part scene** = one scene recorded in several takes. Each PART goes through the
  full pipeline INDIVIDUALLY, then parts are concatenated into one `scene_final.mp4`.
- **Final concat** = joining ALL finished scenes into the upload-ready video (Step 6).

**CRITICAL DISTINCTION:** "concat parts of a multi-part scene" (Step 5b) ≠ "final concat of
all scenes" (Step 6). Parts are joined AFTER silence removal. Scenes are joined after ALL
scenes are ready.

## Step 1: Trim each scene

- Transcribe around the cut points to find exact word boundaries.
- `ffmpeg -i <input> -ss <start> -t <end> ...NVENC...` — ALWAYS re-encode, NEVER `-c copy`.

## Step 2: Normalize audio to −14 LUFS — BEFORE silence removal (Branch A only)

**Branch A (single mixed track): normalize BEFORE auto-editor, NOT after.** Without it,
quiet scenes get over-cut (the threshold treats quiet speech as silence). Normalization
equalizes all scenes so threshold 0.14 behaves consistently.
**Branch B (separate voice track): feed the RAW file — see `../cutting.md`** (normalizing a
demo-recording first destroys the speech/pause gap).

```bash
ffmpeg-normalize scene.mp4 -o scene_norm.mp4 -t -14 -tp -1.5 -c:a aac -b:a 256k
```

- Scenes with volume drift (OS auto-gain): fix BEFORE normalizing:
  `ffmpeg -y -i input.mp4 -af "volume=-4dB:enable='gte(t,240)'" -c:v copy -c:a aac -b:a 256k output.mp4`
- Verify: `ffmpeg -i <file> -af loudnorm=print_format=summary -f null -` → ~−14 LUFS.

## Step 3: Ensure uniform format

- ALL scenes must match: resolution, fps, pix_fmt, codec.
- A scene differs (e.g. 1440p30 vs 1080p60) → re-encode: `-vf "scale=1920:1080" -r 60`.
- Verify before concat: `ffprobe -select_streams v -show_entries stream=width,height,r_frame_rate,pix_fmt`.

## Step 4: Remove specific phrases (if needed)

```bash
ffmpeg -i input.mkv -filter_complex \
  "[0:v]trim=0:END1,setpts=PTS-STARTPTS[v1]; \
   [0:v]trim=START2,setpts=PTS-STARTPTS[v2]; \
   [0:a]atrim=0:END1,asetpts=PTS-STARTPTS[a1]; \
   [0:a]atrim=START2,asetpts=PTS-STARTPTS[a2]; \
   [v1][a1][v2][a2]concat=n=2:v=1:a=1[vout][aout]" \
  -map "[vout]" -map "[aout]" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k output.mp4
```

Many removals → EDL engine (`../cutting.md` Tier 2) builds this for N segments.

## Step 5: Remove silences PER SCENE — BEFORE concat

**auto-editor is O(n²) in file length.** Per scene (1–5 min): seconds each. One combined
25-min file: 30+ minutes. Always cut per scene; a combined file with no alternative → run in
background and expect a long wait.

```bash
# Branch A input = scene_norm from Step 2; flags LOCKED in ../cutting.md
auto-editor scene1_norm.mp4 --edit audio:0.14 --margin 0.12s,0.10s \
  --video-codec h264_nvenc --video-bitrate 10M --audio-bitrate 256k --sample-rate 48000 \
  --no-open -o scene1_final.mp4
```

## Step 5b: Concat parts of MULTI-PART scenes — AFTER silence removal

**NEVER concat parts before auto-editor.** Each part goes through Steps 1–5 individually;
then concat the FINISHED parts.

```
CORRECT:  partA: trim → normalize → auto-editor → partA_final.mp4   (same for B, C)
          concat partA_final + partB_final + partC_final → scene_final.mp4

WRONG:    trim A,B,C → concat → normalize → auto-editor
          (O(n²) blowup, artifacts at joins, wrong normalization)
```

```bash
printf "file '%s'\n" partA_final.mp4 partB_final.mp4 > concat_scene.txt
ffmpeg -f concat -safe 0 -i concat_scene.txt \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k scene_final.mp4
```

## Step 6: Final concatenation — YouTube-optimized (LOCKED)

**1440p upscale is DEFAULT** — YouTube then serves VP9/AV1 instead of AVC1: visibly better
quality for viewers, even those watching at 1080p.

```bash
printf "file '%s'\n" scene1_final.mp4 scene2_final.mp4 > concat.txt

ffmpeg -f concat -safe 0 -i concat.txt \
  -vf "scale=2560:1440:flags=lanczos" \
  -c:v h264_nvenc -preset p7 -tune hq \
  -profile:v high -level 5.1 \
  -rc cbr -b:v 24M \
  -g 120 -bf 2 \
  -spatial-aq 1 -temporal-aq 1 -aq-strength 10 \
  -rc-lookahead 32 \
  -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -movflags +faststart \
  -c:a aac -b:a 384k -ar 48000 \
  FINAL.mp4
```

**⚠️ CRITICAL (production incident, 2026-05-26): the concat DEMUXER can catastrophically
fail on mixed-origin projects.** When scenes come from different encode chains (auto-editor
outputs + externally-rendered segments + an extra audio-only re-encode), the demuxer can
produce a BROKEN file even though every input reports CFR 60. Symptoms: final duration
wildly longer than expected (e.g. 7490 s instead of 1278 s), tiny bitrate (~900 kbps), a
huge `drop=NNNNN` count in the log. The file "decodes clean" but is garbage.

**Fix: use the concat FILTER** — it decodes every input and rebuilds PTS from scratch;
`fps=60` normalizes hidden VFR. Build programmatically for N inputs:

```bash
# files=(scene1_final.mp4 ... sceneN_final.mp4)
args=(); filter=""; i=0
for f in "${files[@]}"; do args+=(-i "$f"); filter+="[$i:v:0][$i:a:0]"; i=$((i+1)); done
filter+="concat=n=${#files[@]}:v=1:a=1[cv][a];[cv]fps=60,scale=2560:1440:flags=lanczos,setsar=1[vs]"
ffmpeg -y "${args[@]}" -filter_complex "$filter" -map "[vs]" -map "[a]" \
  -c:v h264_nvenc -preset p7 -tune hq -profile:v high -level 5.1 \
  -rc cbr -b:v 24M -g 120 -bf 2 -spatial-aq 1 -temporal-aq 1 -aq-strength 10 -rc-lookahead 32 \
  -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -movflags +faststart \
  -c:a aac -b:a 384k -ar 48000 FINAL.mp4
```

Demuxer is OK for truly identical-origin files; **the filter is the safe default when
sources are mixed. ALWAYS verify `final duration ≈ sum of scene durations` after concat** —
the cheapest way to catch this failure.

**Why these settings (each one tested):**

- `-rc cbr -b:v 24M` — YouTube-recommended for 1440p60. CBR forces stable bitrate even on a
  static talking head; VBR/CQ tested → only ~8 Mbps on talking-head → YouTube degrades quality.
- `-preset p7 -tune hq` — maximum NVENC quality; final file only.
- `-profile:v high -level 5.1` — H.264 Level 5.1 is REQUIRED for 2560x1440@60; level 4.2
  tops out at 1080p → "Invalid Level" error.
- `-g 120` — 2-second GOP at 60 fps, YouTube standard for DASH/HLS segmentation.
- `-spatial-aq 1 -temporal-aq 1 -aq-strength 10` — preserves face detail, stabilizes flat backgrounds.
- `-colorspace/-color_primaries/-color_trc bt709` — explicit SDR tags, prevents color misinterpretation.
- `-movflags +faststart` — YouTube starts processing during upload.
- `-c:a aac -b:a 384k -ar 48000` — high-quality source for YouTube's own re-encode.

Expected output: ~24 Mbps (~13 GB for a 75-min video).

**Do NOT use for concat:** `-fflags +genpts+igndts` (A/V desync with B-frames) ·
`-c copy` (frozen frames) · `-level 4.2` at 1440p (Invalid Level) · VBR/CQ without a target
bitrate (starves talking-head footage).

## Step 6b: Pre-concat loudness verification

**ALWAYS verify all scenes before the final concat.** Expected: −13.7 to −14.1 LUFS
(deviation <0.4 dB).

```bash
for f in *.mp4; do
  lufs=$(ffmpeg -hide_banner -i "$f" -af loudnorm=print_format=summary -f null - 2>&1 \
         | grep "Input Integrated" | sed "s/.*: *//")
  printf "%-25s %s\n" "$f" "$lufs"
done
```

## Step 7: Final loudness normalization — NOT NEEDED

Loudness was normalized PER SCENE (Step 2); all scenes are already −14 LUFS. After the final
concat, run ONLY the true-peak fix (`production-rules.md`).
