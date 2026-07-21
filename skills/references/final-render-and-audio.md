# Final Render — overlays + audio mixing in ONE pass

Loaded on demand. The ONE-PASS final render (all overlays + music + ducking) and the audio
mixing canon. The music-selection and SFX-placement DECISIONS live in `../sound.md`; this
file is the execution reference.

## THE GOLDEN RULE: everything in ONE ffmpeg command

**ALL overlays (text, emoji, images) + ALL audio (music, SFX, ducking) = ONE render pass.**
Multiple `-i` inputs are NOT multiple renders — ffmpeg reads them all simultaneously.
This avoids cascading quality loss (each extra AAC/H.264 generation degrades irreversibly).

## Audio rules

- **loudnorm** (good): raises the average level evenly, minimal noise amplification.
- **Compressor for normalization** (bad): pumps noise between words.
- **afftdn** (bad): "barrel"/underwater artifact on clean recordings.
- YouTube normalizes DOWN (loud → −14 LUFS) but never UP — a quiet upload stays quiet.
  Record at −12…−6 dB peaks → normalize to −14 LUFS → clean result.
- **Multi-scene equalization:** measure all scenes, boost quiet ones with plain `volume=XdB`
  BEFORE concat; loudness normalization happens per scene (see `multiscene-pipeline.md`).
- **Cascading AAC:** 256k is the speech ceiling; ideally process in WAV and encode AAC once.

## 🎵 Music under voice — EQ pocket + GENTLE duck (LOCKED, researched + tested 2026-06-22)

**The amateur mistake (we made it first):** heavy sidechain ducking that drops the music
toward silence under speech → the music "dissolves into noise" and is never heard as music.
Over-ducking beyond ~9–12 dB, or burying the bed 20–25 dB below a compressed voice, kills it.

**The professional fix = carve frequency space, don't crush volume.** All music tracks go to
one bus, EQ carves a vocal "pocket", then the duck only needs to be gentle:

```
[bg][intro][outro] → amix=normalize=0 →
  equalizer=f=1500:t=q:w=1.2:g=-4    # vocal-intelligibility pocket (1–2 kHz) — the key move
  equalizer=f=350:t=q:w=1.5:g=-3     # de-mud the low-mids
  → sidechaincompress=threshold=0.05:ratio=2:attack=20:release=700   # gentle: ~2–6 dB dip
[voice][music_ducked][sfx…] → amix=normalize=0:duration=first
```

- **The EQ pocket at ~1.5 kHz (−3…−5 dB) does the separation** — music stays LOUD and
  clearly audible while the voice cuts through.
- **Dip music only 2–6 dB during speech, NEVER to silence.** Pads/cinematic: 2–4 dB, slow
  (attack ~20 ms, release 600–1000 ms). Busy beds: up to 6–9 dB, ratio 2–4.
- **Levels relative to voice at −14 LUFS:** busy bed ≈ 16–18 dB below (≈ −30 LUFS);
  cinematic pad only ~8–12 dB below (≈ −25 LUFS) + EQ pocket — pads have low transient
  energy and don't mask consonants, so they can sit louder.
- **Pick the LOUD/melodic part of a cinematic track** (skip quiet intros with
  `atrim=START:END`) — a quiet ambient intro at low level under voice reads as "noise".
  Verify track loudness over time with `volumedetect` per 15 s window.
- **SFX accents (whoosh/kick on chapter cards) bypass the duck** — short, play at full
  level, mixed separately.
- Sources: BBC/W3C background-music guidance, iZotope EQ carving, sidechain ducking guides.

## CRITICAL: `amix normalize=0`

**ALWAYS use `normalize=0` with amix.** Without it, amix divides each input by 1/N — the
voice loses 50–66% of its volume (measured: −19 dB → −31 dB).

## Workflow

1. **Collect all overlay requests:** exact timecodes, text, duration, type → build a table.
2. **Create PNG overlays with Pillow** (canvas MUST match video resolution;
   `stroke_width`+`stroke_fill`; test on an extracted frame — instant). See `playbooks.md` P5.
3. **Test on a 30–40 s clip** containing ≥1 drawtext AND ≥1 PNG overlay + the audio mix
   (verify ducking + `normalize=0`). Show the user, get approval.
4. **Run the full render in the background.** Expect ~0.8–1.0x realtime for 1440p CBR 24M
   with overlays.

## Command structure template

```bash
ffmpeg -y \
  -i video.mp4 \
  -i overlay1.png -i overlay2.png \            # PNG overlays
  -i stinger.mp3 \                             # SFX
  -stream_loop -1 -i music.mp3 \               # looped bed
  -filter_complex "
    [0:v]                                       # VIDEO CHAIN:
    drawtext=...enable='between(t,S1,E1)',      # plain text (chain with commas)
    drawtext=...enable='between(t,S2,E2)'
    [td];
    [td][1:v]overlay=...:enable='...'[ov1];     # PNG overlays (sequential chain)
    [ov1][2:v]overlay=0:0:enable='...'[vout];

    [0:a]asplit=2[speech][sc];                  # AUDIO CHAIN (voice → mix + sidechain key)
    [3:a]adelay=...,volume=...,afade=...[sfx];  # each insert: delay, volume, fade
    [4:a]volume=...[bg];                        # bed: volume envelope
    [bg][sc]sidechaincompress=threshold=0.05:ratio=2:attack=20:release=700[bg_ducked];
    [speech][sfx][bg_ducked]amix=inputs=3:normalize=0:duration=first[aout]
  " \
  -map "[vout]" -map "[aout]" \
  -c:v h264_nvenc ... -c:a aac -b:a 384k \
  output.mp4
```

## Mixing levels (LOCKED — tested on real videos)

Relative volumes that survived listening tests (voice at −14 LUFS):

| Parameter | Value | Why |
|---|---|---|
| Background bed volume | **~0.08 (8%)** | Subtle atmosphere. Tested 6–21%; ~8% won |
| Intro music | 0.14 | Sets mood, fades out before the bed starts |
| Cinematic insert | 0.19 | Intentional musical moment |
| Percussion/energy insert | 0.135 | Energy for action sections |
| Outro | 0.19 | Closing music |
| **Bed during inserts** | **0% (OFF)** | **Background MUST be silent when any other music plays. NEVER overlap two tracks** |
| Music `-ss 15` / `atrim` | Skip quiet intro | A quiet ambient intro under voice = "noise" |
| `stream_loop -1` | Loop the bed | Short track covers the whole video |
| Duck amount | 2–6 dB (ratio ≈ 2) | Music dips during speech, never vanishes |
| Duck attack / release | 20 ms / 600–1000 ms | Smooth dip, natural return |
| `amix normalize=0` | **ALWAYS** | Prevents voice volume loss |
| `duration=first` | Match video length | All tracks trimmed to the video |

## Volume automation for the bed (fade out for inserts, back in after)

```
volume='if(lt(t,T_START),0,
  if(lt(t,T_FADEIN_END),VOL*(t-T_START)/FADE_DUR,
  if(lt(t,T_FADEOUT_START),VOL,
  if(lt(t,T_FADEOUT_END),VOL*(T_FADEOUT_END-t)/FADE_DUR,
  0))))':eval=frame
```

Nest `if()` blocks per section: `0 → fade_in → hold → fade_out → 0 → …`

## adelay for timed audio inserts

```
[N:a]adelay=MS|MS,volume=VOL,afade=...,atrim=0:END,asetpts=PTS-STARTPTS[name]
```

- `adelay` is in **milliseconds** (120000 = 120 s) and MUST come BEFORE `atrim`.
- `afade` st= values are absolute (include the delay offset).

## Errors we made (learn from them)

| Error | What happened | Fix |
|---|---|---|
| `amix` without `normalize=0` | Voice lost 10+ dB | Always `normalize=0` |
| Heavy ducking (high ratio) | Music vanished under speech | EQ pocket + gentle duck (2–6 dB) |
| Pillow offset-copy borders | Looked different from drawtext | `stroke_width` + `stroke_fill` |
| PNG canvas ≠ video resolution | Overlays wrong size/position | Canvas MUST match video res |
| drawtext colored emoji | Monochrome glyphs | Pillow PNG + emoji font + `embedded_color=True` |
| drawtext strikethrough | Not possible | Pillow `draw.line()` |
| `atrim` before `adelay` | Audio ended early | `adelay` first, then `atrim` |
| Testing overlays on full video | Slow iteration | Test on one extracted frame (instant) |
| "Surgical" insert with `-c copy` | Frozen frames at splice | Always re-encode; one-pass final |

## Do NOT

- `normalize=1` (amix default) — kills voice volume.
- Music with vocals — competes with speech.
- Skip `afade` on music — abrupt start/end.
- `-c:v copy` when changing audio with `-ss` — frozen frames.
- Overlap the bed with any other music track.
