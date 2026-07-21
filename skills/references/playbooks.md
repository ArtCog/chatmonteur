# Operation Playbooks — one playbook per operation

Loaded on demand. Hard rules (NVENC re-encode, never `-c copy`, auto-editor only for silence)
live in `production-rules.md` and always apply.

## P1. Silence/pause removal

Fully covered by `../cutting.md` (Tier 1 — locked thresholds, branch routing, preview gate).
Do not reinvent here. auto-editor renders directly; never export XML and re-render yourself.

## P2. Phrase removal (surgical)

1. Transcribe with word timestamps → find the exact word boundaries.
2. Trim points: word_end + ~0.15 s buffer.
3. Cut with `-filter_complex` `trim/atrim + concat` (single pass — template in
   `multiscene-pipeline.md` Step 4). For many removals, use the EDL engine (`../cutting.md` Tier 2).
4. ALWAYS re-encode with NVENC.

## P3. Concatenation

**All clips MUST have identical format** (resolution, fps, pix_fmt). If not → re-encode first.

```bash
printf "file '%s'\n" clip1.mp4 clip2.mp4 > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k output.mp4
```

Mixed-origin sources (different encode chains) → the concat **filter**, not the demuxer:
see `multiscene-pipeline.md` Step 6 for the failure mode and the safe command.

## P4. Subtitles

Follow `../subtitles.md` (locked standard: sentence case, ≤2 lines, CPL/CPS limits, brand
styling via force_style). Karaoke/word-by-word → `effects.md`.

## P5. Text overlays / lower thirds

**Brand kit overrides generics.** If the project has a brand kit (fonts, colors, motion
rules in `assets/brand/`), ALL on-screen text uses it — not the generic styles below.
Brand-kit conventions that proved out in production:

- One display font (full charset for the target language), baked static TTF in `assets/fonts/`.
- Accent color for emphasis on dark/clean backgrounds; reserve red for danger only.
- **Placement rule: only on clean backgrounds. NEVER cover important on-screen content**
  (numbers, tables, terminal commands, the thing the viewer must read).
- Motion: subtle alpha fade in/out (~0.3 s). No jitter/shake for calm brands.
- Confirm the EXACT overlay wording with the user before rendering.

**Decision tree — which approach:**

```
Plain text only (no emoji, no strikethrough) → A: drawtext
Text + colored emoji (🥲, 🙉, …)             → B: Pillow PNG + overlay
Strikethrough text                            → B: Pillow PNG (drawtext can't strike)
Image overlay (photo, screenshot)             → C: image with soft frame
Many timed text entries (10+)                 → D: ASS subtitles
```

**Critical lessons (learned the hard way):**

- `drawtext` CANNOT render colored emoji — only monochrome glyphs. Use Pillow +
  an emoji font with `embedded_color=True` (Windows: `seguiemj.ttf`).
- `drawtext` CANNOT do strikethrough — use Pillow `draw.line()`.
- `amix` divides volume by N by default → ALWAYS `normalize=0` (see `final-render-and-audio.md`).
- All overlays can be combined in ONE ffmpeg command (chained drawtext + multiple overlay inputs).
- Test on a single extracted frame first (Pillow composite — instant), then render.

**A: brand accent overlay — drawtext with fade, no shake:**

```
drawtext=fontfile='assets/fonts/<Brand>.ttf':text='EXACT WORDING':\
  fontcolor=0xACCENT:fontsize=92:borderw=4:bordercolor=0x000000@0.9:\
  x=(w-tw)/2:y=h*0.11:\
  alpha='if(lt(t,T0+0.3),(t-T0)/0.3,if(gt(t,T1-0.3),(T1-t)/0.3,1))':enable='between(t,T0,T1)'
```

Generic loud variant (non-branded quick edits): big bold system font, shake via
`x=(w-tw)/2+3*sin(t*15)`, `y=(h-th)/2+3*cos(t*12)`.

Chain multiple drawtext with commas (no semicolons):
```
[0:v]drawtext=...enable='between(t,100,104)',drawtext=...enable='between(t,200,203)'[vout]
```

**B: Pillow PNG overlay (emoji, strikethrough, styled graphics):**

```python
from PIL import Image, ImageDraw, ImageFont

# Canvas MUST match video resolution (e.g. 2560x1440), else position/scale are wrong
img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("assets/fonts/Brand-Bold.ttf", 200)
emoji_font = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 120)

text = "Text"
bbox = draw.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx, ty = 1920//2 - tw//2, 1080//2 - th//2

# stroke_width + stroke_fill (NOT offset-copy loops) — matches ffmpeg drawtext look
draw.text((tx, ty), text, font=font, fill=(255, 68, 68, 255),
          stroke_width=5, stroke_fill=(255, 255, 255, 255))
# Diagonal strikethrough:
draw.line([(tx-15, ty+th+10), (tx+tw+15, ty-10)], fill=(255, 34, 34, 255), width=12)
# Colored emoji (MUST use embedded_color=True):
draw.text((tx+tw+50, ty+20), "🥲", font=emoji_font, embedded_color=True)
img.save("overlay.png")
```

Apply in ffmpeg (sequential overlay chain):
```
[0:v]drawtext=...[td];[td][1:v]overlay=0:0:enable='between(t,T1,T2)'[ov1];[ov1][2:v]overlay=...[vout]
```

Preview on a frame BEFORE rendering:
```python
frame = Image.open("test_frame.png").convert("RGBA")
Image.alpha_composite(frame, Image.open("overlay.png")).convert("RGB").save("preview.jpg", quality=95)
```

**C: image overlay with soft frame** — resize photo, rounded-rect panel behind it
(`rounded_rectangle` + `GaussianBlur` glow), paste both onto a transparent full-res canvas,
then overlay as PNG.

**D: ASS subtitles** for many timed entries:
```bash
ffmpeg -y -i scene.mp4 -vf "ass='C\:/path/subs.ass'" -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k output.mp4
```
ASS tags: `\fad(in_ms,out_ms)`, `\move(x1,y1,x2,y2)`, `\blur`, `\t(style)`.

**All overlays are applied in ONE render pass on the final video** (collect every timestamp →
one ffmpeg command, together with music/ducking — `final-render-and-audio.md`). "Surgically
inserting" into an already-rendered file causes artifacts.

## P6. B-roll / image insert

Image overlay with fade → `ffmpeg-cookbook.md`. Placement decisions (WHERE b-roll goes) →
`../motion.md` (visual-interest rules).

## P7. Oval/circular webcam mask

**Step 1: find the exact webcam rectangle (pixel analysis — NEVER guess; position varies
between recordings).**

```python
from PIL import Image
import numpy as np
img = np.array(Image.open('frame.png'))
# TOP edge: scan rows for a sharp brightness jump in the webcam x-range
for y in range(800, 950):
    if abs(int(np.mean(img[y-3:y, 50:300, :])) - int(np.mean(img[y:y+3, 50:300, :]))) > 30:
        print(f'Top edge: y={y}'); break
# RIGHT edge: scan columns for a sharp brightness drop in the webcam y-range
for x in range(250, 450):
    if abs(int(np.mean(img[950:1050, x-2:x, :])) - int(np.mean(img[950:1050, x:x+2, :]))) > 30:
        print(f'Right edge: x={x}'); break
```

Key: brightness gradient >30 between adjacent rows/columns. Verify visually: draw colored
outlines (rect + oval) on the frame, crop, inspect before rendering.

**Step 2: apply the oval mask:**

```bash
# CAM_X, CAM_Y, CAM_W, CAM_H = detected rectangle; CX=CAM_W/2, CY=CAM_H/2, RX=CX-4, RY=CY-4
ffmpeg -y -i input.mp4 -filter_complex "
[0:v]scale=1920:1080,split[main1][main2];
[main2]crop=CAM_W:CAM_H:CAM_X:CAM_Y,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(pow(X-CX,2)/pow(RX,2)+pow(Y-CY,2)/pow(RY,2),1),255,0)'[oval];
[main1]drawbox=x=CAM_X:y=CAM_Y:w=CAM_W:h=CAM_H:c=0x111111:t=fill[bg];
[bg][oval]overlay=CAM_X:CAM_Y" \
-c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -c:a aac -b:a 256k output.mp4
```

How: split → crop webcam + geq ellipse alpha → dark fill under it → overlay back.

## P8. Dynamic zoom

Transcribe → classify moments: normal (1.0x), emphasis (1.15x), critical (1.3x).
Zoom placement rules ("every ~3 s something changes") → `../motion.md`.

## P9. Audio operations

- **Extract:** `ffmpeg -i v.mp4 -vn -c:a copy audio.aac`
- **Replace:** `ffmpeg -i v.mp4 -i new.mp3 -c:v copy -map 0:v -map 1:a -shortest out.mp4`
- **Audio-only filters may keep `-c:v copy`** — video untouched is safe when only audio changes.

## P10. Loudness normalization

**ALWAYS the last step, once, on the final file.**

```bash
# Option A (BEST — two-pass linear, pure gain, zero artifacts):
ffmpeg-normalize final.mp4 -o output.mp4 -t -14 -tp -1.5 -c:a aac -b:a 256k
# Option B (one-pass loudnorm, acceptable — acts as a light compressor):
ffmpeg -i final.mp4 -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 256k output.mp4
```

Then the true-peak fix (`production-rules.md`).

## P11. Color grading

Quick cinematic / vignette / LUT one-liners → `ffmpeg-cookbook.md` and `effects.md`.
Always `-pix_fmt yuv420p` + NVENC.
