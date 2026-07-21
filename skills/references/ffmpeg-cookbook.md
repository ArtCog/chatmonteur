# FFmpeg Cookbook — proven patterns

Loaded on demand. Hard correctness rules live in `production-rules.md` — they always apply
(never `-c copy` for cuts, never select/aselect filters, always re-encode, `-pix_fmt yuv420p`).

## NVENC presets (any NVENC-capable GPU; no NVENC → `libx264` with equivalent CRF)

| Use case | Preset | CQ | Notes |
|----------|--------|-----|-------|
| Quick preview | p1 | 24 | Fastest, lower quality |
| Standard edit | p4 | 20 | Good balance (DEFAULT) |
| Final render | p7 + hq | 18 | Best quality, slower — final concat ONLY |
| Archive | p4 | 16 | High quality, larger files |

```bash
# Standard (default for intermediate renders)
-c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k

# Quick preview
-c:v h264_nvenc -preset p1 -cq 24 -pix_fmt yuv420p -c:a aac -b:a 128k
```

Heavy settings (1440p upscale, p7, CBR 24M) go on the FINAL concat only, never on per-scene
renders — see `multiscene-pipeline.md`.

## Micro-fades at edit points

Professional editors apply ~5 ms micro-fades at every edit boundary — eliminates clicks/pops.

```bash
# 5ms fade at output boundaries
-af "afade=t=in:d=0.005,afade=t=out:st=DURATION-0.005:d=0.005"

# Per-segment micro-fade (in filter_complex):
[0:a]afade=t=out:st=END-0.005:d=0.005[a0];
[1:a]afade=t=in:d=0.005[a1];
[a0][a1]concat=n=2:v=0:a=1[aout]
```

**Why NOT `acrossfade` for speech:** it fades out the tail of clip1, clipping the last word's
ending. For speech, use clean concat with micro-fades.

## Voice cleanup chain (order matters)

```bash
# highpass → lowpass → compressor → de-esser  (loudness normalization comes LAST, separately)
-af "highpass=f=80,lowpass=f=12000,acompressor=threshold=-20dB:ratio=4:attack=10:release=100:makeup=10,equalizer=f=6500:t=q:w=2:g=-4"
```

| Stage | Filter | Purpose |
|-------|--------|---------|
| 1 | `highpass=f=80` | Remove room rumble, mic handling noise |
| 2 | `lowpass=f=12000` | Remove hiss, high-frequency noise |
| 3 | `acompressor=threshold=-20dB:ratio=4:attack=10:release=100:makeup=10` | Even out voice dynamics |
| 4 | `equalizer=f=6500:t=q:w=2:g=-4` | De-ess (tame harsh "s" sounds) |

Do NOT add `afftdn` noise reduction on clean recordings — "barrel"/underwater artifact
(see `known-issues.md`). Loudness target is **−14 LUFS** (YouTube), applied once on the
final master — see `final-render-and-audio.md`.

## xfade + clean audio concat (NOT acrossfade)

```bash
# 2 clips with fade transition — audio: clean concat with micro-fades
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v][1:v]xfade=transition=fade:duration=0.3:offset=PREV_DUR-0.3,format=yuv420p[vout]; \
   [0:a]afade=t=out:st=PREV_DUR-0.005:d=0.005[a0]; \
   [1:a]afade=t=in:d=0.005[a1]; \
   [a0][a1]concat=n=2:v=0:a=1[aout]" \
  -map "[vout]" -map "[aout]" -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p output.mp4
```

`offset` = duration_of_first_clip − transition_duration. `format=yuv420p` after xfade is
mandatory — xfade can emit yuv444p, which breaks Windows Media Player (error 0x80004005).

## J-cut (audio leads video)

Audio from clip2 starts ~0.5 s before the video transition — smooth, natural flow.

```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=CLIP1_DUR-0.5,format=yuv420p[vout]; \
   [0:a]atrim=0:CLIP1_DUR-0.5,afade=t=out:st=CLIP1_DUR-1.0:d=0.5[a0]; \
   [1:a]afade=t=in:d=0.3[a1]; \
   [a0][a1]concat=n=2:v=0:a=1[aout]" \
  -map "[vout]" -map "[aout]" -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p output.mp4
```

## Color grading

```bash
# Quick cinematic look (no LUT needed)
-vf "eq=brightness=0.06:contrast=1.15:saturation=1.2"

# With 3D LUT file (.cube) — LUT pack in assets/luts/
-vf "lut3d=file=cinematic.cube"

# Vignette (darken edges)
-vf "vignette=PI/4"

# Combine: color grade + vignette
-vf "eq=brightness=0.06:contrast=1.15:saturation=1.2,vignette=PI/4"
```

## Circular crop mask

```bash
# Make video region circular (diameter=SIZE)
scale=250:250,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(pow(X-125,2)+pow(Y-125,2),pow(122,2)),255,0)'
```

Full oval-webcam-mask playbook (edge detection, verification) → `playbooks.md` C7.

## Lower third with fade

```bash
drawtext=text='Speaker Name':fontsize=28:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=10:\
x=w-tw-40:y=h-80:\
enable='between(t,5,12)':\
alpha='if(lt(t-5,0.5),(t-5)/0.5,if(lt(12-t,0.5),(12-t)/0.5,1))'
```

## PiP overlay with timing

```bash
ffmpeg -i main.mp4 -i overlay.mp4 \
  -filter_complex "[1:v]scale=320:-1[pip];[0:v][pip]overlay=W-340:20:enable='between(t,10,30)'" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a copy output.mp4
```

## Image overlay with fade in/out

```bash
ffmpeg -i video.mp4 -i image.png \
  -filter_complex "[1:v]format=rgba,fade=t=in:st=10:d=0.5:alpha=1,fade=t=out:st=14.5:d=0.5:alpha=1[img];[0:v][img]overlay=(W-w)/2:(H-h)/2:enable='between(t,9.9,15.1)'" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a copy output.mp4
```

## Ken Burns effect (zoom/pan on still image)

```bash
# Slow zoom in over 10 seconds
ffmpeg -loop 1 -i image.jpg -t 10 \
  -vf "zoompan=z='min(zoom+0.001,1.3)':d=300:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p output.mp4
```

## Speed change

```bash
# 2x:   -vf "setpts=0.5*PTS" -af "atempo=2.0"
# 0.5x: -vf "setpts=2.0*PTS" -af "atempo=0.5"
```

## Subtitle burn-in

Follow the locked standard in `../subtitles.md` (casing, CPL/CPS, styling). Mechanics:

```bash
ffmpeg -i video.mp4 \
  -vf "subtitles=subs.srt:fontsdir='assets/fonts':force_style='FontName=<Font>,FontSize=64,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=4,Shadow=1,MarginV=95,Alignment=2'" \
  -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a copy output.mp4
```

ASS/SRT colors are **BGR hex** `&HAABBGGRR`. Custom fonts need `fontsdir`.

## Music + ducking

Do not improvise here — the professional mix (EQ pocket + gentle sidechain, locked levels)
lives in `../sound.md` and `final-render-and-audio.md`.

## Windows path notes

- Use forward slashes in ffmpeg args: `C:/path/video.mp4`; wrap paths with spaces in quotes.
- Inside filter strings escape the drive colon: `C\:/path/file.ttf`.
- Very long `-filter_complex`? Put it in a file: `-filter_complex_script file.txt`.
