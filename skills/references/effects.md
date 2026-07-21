# Effects — karaoke captions, xfade transitions, LUTs

Loaded on demand. Word-by-word animated captions, scene transitions, one-line color grading.

## Animated captions (karaoke / CapCut-style)

Word-by-word highlight using ASS `\kf` tags. Requires: `pysubs2`, `faster-whisper`.
**Pipeline:** faster-whisper word timestamps → pysubs2 ASS with `\kf` → ffmpeg NVENC burn.

```python
import pysubs2
from faster_whisper import WhisperModel

model = WhisperModel('large-v3', device='cuda', compute_type='float16')
segments, _ = model.transcribe('scene.mp4', language=LANG, word_timestamps=True)
words = [w._asdict() if hasattr(w, '_asdict') else vars(w)
         for seg in segments for w in seg.words]

subs = pysubs2.SSAFile()
subs.info['PlayResX'], subs.info['PlayResY'] = '1920', '1080'
subs.styles['Default'] = pysubs2.SSAStyle(
    fontname='Impact', fontsize=90, bold=True,
    primarycolor=pysubs2.Color(255, 255, 255, 0),   # white base
    secondarycolor=pysubs2.Color(0, 255, 255, 0),   # sweep color — BGR! (0,255,255)=yellow
    outlinecolor=pysubs2.Color(0, 0, 0, 0), outline=5, shadow=3,
    alignment=2, marginv=220)                        # lower-center

for i in range(0, len(words), 3):  # 3 words per line
    group = words[i:i+3]
    start_ms, end_ms = int(group[0]['start']*1000), int(group[-1]['end']*1000)
    text = ' '.join('{\\kf' + str(max(int((w['end']-w['start'])*100), 5)) + '}' + w['word']
                    for w in group)
    subs.append(pysubs2.SSAEvent(start=start_ms, end=end_ms+300, text=text))
subs.save('captions.ass')
```

**Render:** `ffmpeg -i video.mp4 -vf "subtitles='C\:/path/captions.ass'" -c:v h264_nvenc ...`

**ASS colors are BGR, not RGB:** `(0,255,255)` = yellow, `(255,255,0)` = cyan.

Fonts ship in `assets/fonts/` (the user's brand kit can add more); on Windows the system
Impact/Arial/Tahoma also work. Battle-tested styles: Impact 90px yellow sweep at
`marginv=220` (lower-center).

## xfade transitions (between scenes)

30+ built-in ffmpeg transitions. Use between scenes for polish.

```bash
ffmpeg -i scene1.mp4 -i scene2.mp4 -filter_complex \
  "[0:v]trim=end=END1,setpts=PTS-STARTPTS[v0]; \
   [1:v]trim=start=0,setpts=PTS-STARTPTS[v1]; \
   [v0][v1]xfade=transition=fade:duration=1:offset=OFFSET,format=yuv420p[vout]; \
   [0:a]atrim=end=END1,asetpts=PTS-STARTPTS[a0]; \
   [1:a]atrim=start=0,asetpts=PTS-STARTPTS[a1]; \
   [a0][a1]acrossfade=d=1[aout]" \
  -map "[vout]" -map "[aout]" -c:v h264_nvenc ... output.mp4
```

- **Talking-head:** `fade`, `dissolve`, `smoothleft` · **Flashy:** `circlecrop`, `radial`,
  `pixelize`, `zoomin`, `diagtl` · **Slide:** `slideleft/right/up/down`
- `offset` = duration_of_first_clip − transition_duration.
- Always `-pix_fmt yuv420p` (xfade can emit yuv444p).
- `acrossfade` is OK here because scene boundaries sit in silence; for mid-speech joins use
  clean concat with micro-fades (`ffmpeg-cookbook.md`).

## LUT color correction

One-line color grading with `.cube` LUT files (pack in `assets/luts/`; the user can drop in
their own):

```bash
ffmpeg -i input.mp4 -vf "lut3d='assets/luts/warm_film.cube'" -c:v h264_nvenc ... output.mp4
```
