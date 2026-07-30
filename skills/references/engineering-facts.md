# Engineering facts — the numbers that make an edit look/sound professional

Mined 2026-07-30 from OpenMontage (AGPL — knowledge only, never code), the commercial
market, editing-craft sources and the open-source landscape. **Parameters and algorithms
are facts, not expression: reimplementing them is legitimate.** Anything that is somebody's
creative design (a palette, a specific card layout) is excluded on purpose.

Each entry: the value, why it works, where it lives in our code.

## Sound

| Fact | Value | Why | Ours |
|---|---|---|---|
| Ducking is **sidechain compression**, not a volume dip | `sidechaincompress=threshold=0.02:ratio=9:attack=200:release=500:level_sc=1:mix=0.9`; speech `asplit`s into a play branch and a key branch | Music yields exactly while a word sounds and returns in the gaps. Measured **8.1 dB** of duck on our synthetic bench | `tools/sound.py` |
| Notch the bed in the **speech band** | `equalizer=f=3000:width_type=o:width=1.6:g=-4` | Intelligibility is won by vacating 2–4 kHz, not by lowering level. Three separate sources call this the single most important mix rule | `tools/sound.py` |
| Music sits **~20 dB under dialogue** | `-20 dB` | W3C accessibility floor for foreground speech; broadcast practice pulls a little more | `_MUSIC_GAIN_DB` |
| SFX **lands before its beat** | −15 ms | Hearing is faster than seeing; a hit on the exact frame reads as late | `_sfx_delay_ms` |
| SFX level | −12…−18 dB, always ≥6 dB under dialogue | Present without competing | `_SFX_GAIN_DB` |
| `amix` needs `normalize=0` | — | Otherwise every extra layer silently attenuates the dialogue ~6 dB | `tools/sound.py` |
| Fade **before** any delay/trim | — | Fading after a delay fades the silence, not the audio | `tools/sound.py` |
| Loudness is the **last** audio step | −14 LUFS / −1.5 dBTP + true-peak limiter | Normalising mid-chain and again at the end double-compresses dialogue | `tools/render.py` |
| Stock beds open sparse | pick the loudest window by `ebur128` momentary + sliding average | A bed that starts on the quiet intro sounds like it is still loading | `_best_segment` |

## Cutting

| Fact | Value | Why | Ours |
|---|---|---|---|
| Silence detection | `silencedetect=noise=-35dB:d=0.5` OR relative-to-peak threshold | Absolute thresholds mis-cut quiet recordings — ours is relative (0.14 of peak), which is why it beat theirs on Arthur's footage | `tools/cut_silence.py` |
| Keep padding around a cut | 0.08–0.12 s each side | Prevents clipped word heads/tails | `cut_silence` margins |
| Merge micro-gaps | drop segments <0.01 s; merge gaps <0.05 s | Otherwise the concat stutters | — |
| Dead air | trim >1.5 s down to ~0.5 s | Below that it reads as natural breathing | agent rule |
| **Protect breaths** | 0.3–0.8 s pauses are meaning, not dead air | Cutting them is the classic robotic tell | agent rule |
| Filler removal is **transcript-driven**, not level-driven | word-level timestamps → cut word spans | Amplitude cannot tell "эм" from a word | D11: agent writes `edl.json` |
| Scene detection | PySceneDetect `content` @ 27.0 (talking head 22, screencast 30); ffmpeg fallback `select='gt(scene,0.3)'` — note the different scales | Per-scene processing of long footage | not yet |
| Speed ramps | `setpts=(1/f)*PTS` + chained `atempo` (valid 0.5–100, chain beyond) | Boilerplate typing 2–3×, installs 2–4× | not yet |

## Rhythm and structure (the craft that reads as "an editor did this")

- **J/L cuts**: offset the picture cut ±0.3–0.8 s from the audio cut. Pure timing maths on data
  we already have — the cheapest upgrade that most changes the feel. *Not built yet.*
- **Cuts per minute by genre**: educational 3–5, vlog 6–10, comedy/gaming 10–20. The 2026 shift
  is that *varying* the rate matters more than hitting a number — a constant pace fatigues.
- **Pace follows the arc**: a target CPM per semantic block (hook fast, explanation by meaning),
  not one rate for the whole video.
- **Hook**: 0–5 s pattern interrupt, 5–15 s payoff of the promise, 15–30 s open the loop. The
  real deadline is 15 s — the steepest retention drop is seconds 10–20.
- **Open loops**: 2–3 per video, close one before opening the next.
- **Pattern interrupt** every 60–90 s; chapters from ~8 min.
- **B-roll doctrine**: ~60/40 A-roll/B-roll; never cut to a *single* insert — group 3+; hold
  2–5 s; return to the face on a new beat, never mid-phrase.
- **Show-don't-tell redundancy is the amateur tell**: an image that literally repeats the noun
  just spoken adds nothing. Ban it.
- **One text layer at a time** — enforced in `tools/storyboard.py`.
- **Stagger**: `min(0.06 s, 0.5 / item_count)` — a group must finish arriving within ~0.5 s.
- **Holds**: fade 0.3–0.5 s; entrance 0.5–1.0 s; count-up 1.2–1.6 s then hold; a chart needs
  2–4 s to build **plus 3–5 s to be read** before you cut away.
- **Label after value** on a stat card — the number lands, then its meaning.

## Screencast (our second footage type)

| Fact | Value |
|---|---|
| Record 4K, deliver 1080p | the 2× headroom is what makes a punch-in stay sharp |
| FPS | 30 for static code, **60 for scrolling/UI motion** |
| Zoom by target | terminal/code 1.5–2.2×, small button 2.0–3.0×, modal 1.4–2.0×, full page 1.0–1.3× |
| Zoom timing | 0.6–0.8 s ease; **hold ≥3 s** before the next move |
| Jump-cut mask | a 1.0→1.02× nudge on the cut hides the seam |
| Cursor | 1.5–2× size, ~50 px highlight ring, pause 0.5 s on target before clicking |
| IDE before recording | font 18–22 px, zoom 150–175 %, minimap off, sidebar collapsed |
| Attention cues | max **2** at once; appear just before the action, clear right after |
| Screencast loudness | −16 LUFS (gentler than −14 for long sessions) + 80 Hz HPF for keyboard rumble |

## Quality gates — the mechanism that blocks a boring edit

The most valuable idea found. Score the PLAN before rendering and refuse the render:

- **Slideshow risk** (0–5, six weighted dimensions): dominant scene type >70 %; unique-description
  ratio <60 %; shot-size repetition >60 %; visuals with no stated role; motion without intent;
  **>60 % of scenes being text cards → "this feels like animated slides"**. ≥4 = fail.
- **Variation**: ≥3 consecutive identical shot sizes; >50 % shot-size repetition; no hero moment;
  generic filler wording.
- **Motion ratio**: a promise like "motion-led" requires ≥70 % real motion — and text/stat cards
  explicitly **do not count** as motion.
- **Source review**: refuse to mark footage "reviewed" without an actual probe having run.

## Libraries worth adopting (permissive only)

MediaPipe (Apache-2.0, face/pose → safe zones, reframe) · PySceneDetect (BSD-3) ·
Silero VAD (MIT, precise speech/non-speech) · WhisperX align (BSD-2, better word timings) ·
DeepFilterNet (MIT/Apache, denoise) · librosa (ISC, beat detection) · pyannote (MIT, diarization).

**Never**: Ultralytics YOLO (AGPL — MediaPipe covers it), essentia/aubio (AGPL/GPL — librosa
covers it), madmom & InsightFace *weights* (non-commercial), Remotion (paid for automation —
HyperFrames covers it), Blender bpy (GPL).

## Handing an edit to a human

Zoom keyframes do **not** survive interchange: OTIO does not standardise transforms, Premiere
cannot read modern FCPXML, Resolve's FCPXML import is version-fragile. So: export clean cut
structure (OTIO/EDL — both import natively, Resolve Free included) **plus** a readable zoom
sheet, instead of gambling on a fragile effect round-trip. Resolve's scripting API needs paid
Studio and cannot even retime — not an engine, only an export target.
