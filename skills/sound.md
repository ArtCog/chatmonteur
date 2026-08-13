# Sound — music beds, SFX, ducking (decisions)

The decision layer for sound design. Execution (filter graphs, locked levels, the one-pass
final render) lives in `references/final-render-and-audio.md` — read it before building the
mix. Nothing is generated: music and SFX come from the bundled CC0 pack, the user's own
drop-in files, and — when the pack has no fitting hit — `stock kind=sfx` (Freesound, needs
`FREESOUND_API_KEY`). It downloads the MP3 preview, not the original: an OAuth2 dance for a
2-second whoosh sitting 15 dB under speech buys nothing. Every candidate carries
`attribution_required` and `noncommercial` in the manifest — CC-BY means a line in the video
description, so prefer CC0 when two candidates are equally good.

## The sound pack

```
assets/sound/
├── ledger.jsonl  licence and SHA-256 authority for every bundled file
├── music/        CC0 background bed
├── sfx/          CC0 UI accent
└── user/         local drop-ins — ALWAYS preferred when present; contents stay untracked
```

Rules for choosing a track:

- **No vocals ever** — vocals compete with speech.
- Background bed: neutral, low transient energy, loopable. Skip quiet ambient intros
  (`atrim`/`-ss`) — a barely-audible intro under voice reads as noise, not music.
- Cinematic pads may sit louder than busy beds (low transient energy doesn't mask
  consonants) — levels table in the reference.
- One bed per video section; **never two music tracks at once** — the bed is OFF (0%)
  during any intro/insert/outro.

## Selection branch — default, custom, or none

Read the active brand's `sound.json` before searching. Then follow exactly one
branch and record it in the video's `PLAN.md` so another agent does not ask again:

1. **Approved brand default exists and the user did not request a special sound:**
   use `default_background` without a new search or question. Resolve its
   `ledger_id` through `assets/sound/ledger.jsonl`.
2. **The user asks for a different mood, a dedicated intro/outro, or per-section
   music:** show the three choices `default_background`, `custom_sections`, and
   `no_music`. For `custom_sections`, ask what belongs in background, intro, and
   outro; `null` means that section stays absent. Search only after this answer.
3. **No approved brand default exists:** ask the same three-way question once.
   Never silently turn a random search result into a recurring channel theme.
4. **The project already records a choice:** reuse it silently unless the user
   changes it.

Every newly selected track still needs a rights ledger and the short human mix
gate below. Approval of a fallback does not make it a permanent signature theme.

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

### Silence is an instrument — use it once, use it hard

Drop the music out entirely for ~2 s at the single emotional centre of the film:
the one line the whole piece was made to deliver. Not three times, not "wherever
it feels quiet" — once. A pause that happens twice stops being a pause and
becomes a gap. If you cannot name which line deserves it, the film has no centre
yet and that is the real finding.

Related, and separate: **the tail fade.** Music fades under the last 3–5 s so the
closing image can breathe without a musical resolution fighting it.

### The L-cut — carry sound across the seam

Let the outgoing scene's audio run 0.5–1.5 s under the incoming picture (or the
reverse: start the next scene's sound before its picture arrives). The ear
crosses the cut before the eye does, so the seam stops registering as a seam.

Use it on the 3–4 hardest transitions in a piece — the ones where the picture
jumps but the thought continues. Everywhere is worse than nowhere: applied to
every cut it becomes mush, and the moments that needed it lose their power.
For a talking head this is most often the join between a screen recording and
the camera, where the voice is continuous and only the picture moves.

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

Before the full render, show a 30–40 s test clip when the track or its levels are
new. Once a recurring brand default and its levels are approved, ordinary videos
may reuse them without repeating the gate; a new track, new gain, intro/outro, or
materially different voice mix reopens it. Music taste is subjective — the user's
ear is the authority.
