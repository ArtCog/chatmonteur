# Sound — music beds, SFX, ducking (decisions)

The decision layer for sound design. Execution (filter graphs, locked levels, the one-pass
final render) lives in `references/final-render-and-audio.md` — read it before building the
mix. Nothing is generated: music and SFX come from the bundled CC0 pack and the user's own
drop-in files.

## The sound pack

```
assets/sound/
├── music/     CC0 background beds, intro/outro, cinematic inserts
├── sfx/       whooshes, clicks, pops, risers — short accents
└── user/      the user's own files — ALWAYS preferred over the bundled pack when present
```

Rules for choosing a track:

- **No vocals ever** — vocals compete with speech.
- Background bed: neutral, low transient energy, loopable. Skip quiet ambient intros
  (`atrim`/`-ss`) — a barely-audible intro under voice reads as noise, not music.
- Cinematic pads may sit louder than busy beds (low transient energy doesn't mask
  consonants) — levels table in the reference.
- One bed per video section; **never two music tracks at once** — the bed is OFF (0%)
  during any intro/insert/outro.

## Where sound goes (placement decisions)

| Moment | Sound | Why |
|---|---|---|
| Video start / hook | Intro music, fades out as the bed starts | Sets mood |
| Talking sections | Background bed, ducked gently under voice | Atmosphere without competing |
| Chapter cards / section changes | Whoosh or riser, full volume (bypasses the duck) | Signals structure |
| Zoom-ins / punch-ins | Optional short accent (click/pop) | Reinforces the motion |
| Graphics reveals | Whoosh synced to the anchor word (±100 ms, `motion.md`) | Visual+audio one gesture |
| Demo/insert moments | Cinematic insert, bed OFF | Intentional musical moment |
| Finale/outro | Outro track, louder than the bed | Closing energy |

Restraint is a feature: an SFX on EVERY cut is amateur. Accent structural moments
(chapters, reveals, the finale), not every jump cut.

## Ducking (the short version — full canon in the reference)

- **EQ pocket first, gentle duck second.** Carve ~1.5 kHz (−3…−5 dB) out of the music so
  the voice cuts through; then sidechain-duck only 2–6 dB. NEVER duck music to silence —
  it dissolves into noise and stops being music.
- `sidechaincompress=threshold=0.05:ratio=2:attack=20:release=700` on the music bus,
  keyed by the voice.
- SFX accents bypass the duck — short, full level, mixed separately.
- **ALWAYS `amix normalize=0`** — the default divides the voice by the input count.

## Order in the pipeline

1. All cutting is finished first (music is NEVER baked into the recording path — a
   continuous layer added at final render can't be chopped by the cutter).
2. Voice is at −14 LUFS (normalized per scene earlier).
3. Music + SFX + overlays go into the ONE final render pass.
4. True-peak fix last (`production-rules.md`).

## Approval

Before the full render: mix a 30–40 s test clip (bed + duck + one SFX + one overlay),
show the user, get approval on levels. Music taste is subjective — the locked defaults are
the starting point, the user's ear is the authority.
