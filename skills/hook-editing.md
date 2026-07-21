# Hook Editing — sidecar voice + visual bank

Read when the hook/intro's accepted VOICE and its VISUAL footage come from SEPARATE
recordings and must be matched by meaning. This is an EDITORIAL task (meaning → shot choice
→ brand), not raw cutting: decide here, execute with `cutting.md` / `references/` mechanics.

## Inputs and roles

Identify and record the role of every source file:

- `voice-hook` — the accepted voice take (**the spine of the timeline**). Usually the
  mic-only track/file.
- `visual-bank` — screen actions, demos, charts, sites; B-roll source only.
- optional curated screenshots (`assets/visual-references/`) — used ONLY when the user
  explicitly asks, or the visual bank truly lacks a needed proof visual.

The voice is the timeline. Visuals are cut, reordered, cropped, zoomed, or sped up to match
it. **NEVER speed up or time-stretch the voice** unless explicitly asked.

## The flow (in order, checkpoints are mandatory)

1. **Transcribe the accepted voice.** ASR mishears brands and key phrases — caption and
   overlay by MEANING, never blindly from the transcript.
2. **Tighten the voice:** remove dead air and false starts (`cutting.md`), keep speech speed
   natural. **Remove silence, not phonemes** — trimming inside a voiced word (e.g. shaving a
   drawn-out consonant) sounds unnatural; it was tried and reverted.
3. **🛑 CHECKPOINT — voice tempo approval BEFORE any visuals.** Ask: too dense or too loose?
   Pauses tighter or more relaxed? Any phrase needs breathing room? Do not proceed without OK.
   (A visual preview rendered before this approval is labeled `preview v1`, never final.)
4. **Study the visual bank yourself, densely** — scrub ~every 1–2 s and map frames to words
   BEFORE proposing anything. Contact-sheet timecodes drift ~2 s vs the real file — verify
   against the actual video. Do NOT make the user point at frames; that is the editor's job.
5. **Build the beat map:** `voice beat → proof/visual → source timecode → crop/motion →
   duration`. Show it as a **labeled storyboard with actual frames** (beat # · voice snippet
   · source timecode) — the user approves visuals visually, not from a text table.
   Extracting frames into a sheet is a seconds-long ffmpeg+PIL job — be fast at SHOWING.
6. **Render** after approval: concat FILTER for visual segments under the voice spine,
   brand overlays in the same pass (`references/final-render-and-audio.md`), final scale,
   then the true-peak fix. Keep the plan (`plans/montage_plan.json`) and the final
   contact sheet with the project.

## The read-script rule (hard)

Before using ANY screen footage, inspect it. Exclude every range where the viewer can see:

- the hook/script text the speaker is reading (teleprompter — usually the first ~minute);
- a prompt or document that exposes the narration before it is spoken;
- large subtitle-like text not intended as final design.

Viewers must never see raw "reading from the screen". Record excluded ranges in the plan:

```json
{"excluded_visual_ranges": [
  {"start": "00:00", "end": "01:06", "reason": "read-script frames visible"}]}
```

## Editorial principle: footage is already in narrative order

Creators typically record the visual bank **in the same logical order as they narrate**
(95–99% of the time the footage follows the story beat by beat).

1. **Default to source order** — walk the visual bank top-to-bottom and map voice beats to
   footage phases in recording order. Path of least resistance, almost always correct.
2. **Meaning may override order when it clearly fits** — a single deliberate semantic anchor
   (a later-recorded proof pinned to an earlier phrase) is good. Chaotic frame-by-frame
   jumping is what's forbidden.
3. **When the user names a specific shot** ("there's a clip where I fly between planets —
   use it for 'Let's go!'"), scrub that region at fine granularity and find the EXACT
   motion — don't settle for a nearby static frame.

## Shot variety (hard lessons — each cost real re-edits)

- **No repeated / too-similar shots; never two similar back-to-back.** Vary the phases
  (terminal / charts / comparison / materials / demo) so consecutive beats look different.
- **A meaningful demo is PROOF, not filler** — place it where it's the actual subject plus
  at most one short finale flourish. Don't minimize it to nothing, don't spray it everywhere.
- **The finale gets room:** ~2–2.5 s, a distinct closing shot (not a repeat). Extend video
  past the voice with a silent tail (`apad` + `-shortest`) if needed. An abrupt 0.7 s
  end-cut always reads as a mistake.
- **Prefer meaning-based visual blocks** — frequent changes only when they match the spoken
  content; don't change visuals under every word just to create motion.
- Every visual segment must justify itself against the spoken phrase it supports. Collected
  reference images are a research library, not automatic B-roll.

## Overlays

- Brand kit locked (one font, one accent color, dark/clean scenes only — `motion.md`).
- **Never cover the proof** — comparison numbers, materials lists, terminal commands. If the
  underlying visual carries meaning, move the overlay or skip it for that beat.
- **Confirm the EXACT wording** of every accent overlay with the user before rendering.
- Preserve aspect ratio always — crop/pad/zoom, never stretch.

## Ask the user vs act autonomously

| ASK first (block until answered) | Act autonomously (just do it, mention it) |
|---|---|
| Voice tempo/density after cleaning (mandatory checkpoint) | Exclude read-script frames |
| The beat map / storyboard before rendering | Map visuals in narrative order, large meaning blocks |
| Exact wording of on-screen accent text | Tighten silence (speech speed stays natural) |
| Inserting an EXTERNAL reference image | Apply brand style |
| A genuinely ambiguous shot choice | Pick the obvious shot; vary adjacent beats |
| Standalone Short vs intro-of-full-video | Crop/pad/scale; final render + true-peak + verify |

Rule of thumb: **editorial direction and anything outward-facing → ask. Execution of an
agreed plan → act.**

## Naming discipline

- `preview` = voice tempo and/or visual pacing NOT yet approved.
- `fixed` = technical true-peak pass applied.
- Nothing is called **final** until the user approves voice tempo AND edit direction.
