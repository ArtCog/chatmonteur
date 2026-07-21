# Motion & Visual Interest — graphics, zooms, b-roll

When to add visual interest, and how to make motion graphics that don't look like AI slop.
Graphics engine: **HyperFrames** (agent-native HTML/CSS/GSAP → MP4). Mechanical overlays
(static text, PiP, image inserts) → `references/playbooks.md` P5–P7 instead — don't spin up
a graphics engine for a lower third.

## Why visual interest exists (the retention math)

- **The ~3-second rule:** every ~3 seconds SOMETHING should change — movement, angle, zoom,
  graphic, sound. A monotone static shot bleeds retention hardest at seconds 4–12.
- **B-roll/inserts enter at attention dips**, and the edit returns to the speaker's face for
  direct contact on key statements.
- **Zoom classification** (from the transcript): normal statement 1.0x · emphasis 1.15x ·
  critical point 1.3x. Punch-ins land on the emphasized WORD, not vaguely near it.
- Graphics illustrate what words can't (numbers, comparisons, structure). If the speaker's
  face and voice already carry the moment, add NOTHING.

## Motion philosophy (locked)

- **Motion serves meaning — never decoration for its own sake.** Modern, clean, dynamic.
- **Easings:** `power3.out` for reveals (element entry, text appearance); `sine.inOut` for
  loops. **NEVER `linear`** — linear motion reads as cheap and mechanical.
- **≥3 different easings per scene** — variety is what makes motion feel designed.
- Subtle alpha fade in/out (~0.3 s) for overlays; no jitter/shake unless the brand is loud.

## Anchor-word sync (locked)

Every animation lands **WITH its key word, tolerance ±100 ms**. The viewer must feel that
visual and speech are one thing. Anchor words come from the word-level timestamps of the
transcript — never eyeballed.

**Take the transcript from the FINAL cut draft** — timings drift after silence removal and
meaning cuts; a transcript of the raw file is useless for sync.

## Typography

Banned fonts (they scream "AI-generated default") — never use:
Inter, Roboto, Open Sans, Lato, Poppins, Outfit, Sora, Fraunces, Playfair Display,
Cormorant Garamond, Syne, Cinzel, Nunito, Source Sans, PT Sans, Arimo.

Pick fonts with character. The project's brand kit (`assets/brand/`) wins over any default;
one display font per video.

## Workflow (approval gates are mandatory)

1. **Storyboard first, render second.** Build a storyboard (beats, anchor words, animation
   type per moment) → show the user → wait for OK. Never render graphics nobody approved.
2. **One composition per scene.** Independent scenes can be built in parallel.
3. **Style-test on a short fragment first.** HyperFrames renders FRAME BY FRAME: a 14 s
   fragment ≈ 30 s, a full 9-min video ≈ 30–40 min. Validate the style cheaply, then run
   the full render in the background.
4. **Speaker video must be all-intra before HF render:** re-encode with `-g 1` (keyframe
   every frame), or the speaker freezes during frame-accurate compositing. The 3–5× file
   size is normal and temporary.
5. HF outputs 1080p → the final render upscales to 1440p (`references/multiscene-pipeline.md`
   Step 6). Frame-by-frame 4K in HF is too slow — don't.
6. **Self-check after render before showing the user:** scrub a timeline strip of frames and
   verify sync/placement yourself first.

## Placement rules

- Graphics/text only on clean areas. **NEVER cover the thing the viewer must see** —
  numbers, tables, terminal commands, demos.
- Confirm the EXACT overlay wording with the user before rendering (ASR mishears brands;
  a typo burned into video costs a re-render).
- Captions and graphics must not collide — if both are present, captions stay lower-center,
  graphics take the upper half.
