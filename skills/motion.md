# Motion & Visual Interest — graphics, zooms, b-roll

When to add visual interest, and how to make motion graphics that don't look like AI slop.
Graphics engine: **HyperFrames** (agent-native HTML/CSS/GSAP → MP4). Mechanical overlays
(static text, PiP, image inserts) → `references/playbooks.md` P5–P7 instead — don't spin up
a graphics engine for a lower third.

## Why visual interest exists (the retention math)

- **Change something on a meaning boundary, not on a timer.** Something should shift as each
  new idea lands — movement, angle, zoom, graphic, sound. A monotone static shot bleeds
  retention hardest early.
- **B-roll/inserts enter at attention dips**; for a talking-head, the edit returns to the face
  for direct contact on key statements (for voice-over, B-roll IS the visual channel — near-constant).
- **Zoom classification** (from the transcript): normal statement 1.0x · emphasis 1.15x ·
  critical point 1.3x. Punch-ins land on the emphasized WORD, not vaguely near it.
- Graphics illustrate what words can't (numbers, comparisons, structure). If face and voice
  already carry the moment, add NOTHING.

## Pacing & style (target: educational-explainer + Fireship density, NOT MrBeast)

Density comes from information-per-second, not stimulation-per-second. (MrBeast's own team
slowed their cutting in 2024 — 38→23 cuts/min — and grew faster; a tech audience fatigues on
overstim fastest.) Concrete cadence:

- **First ~15 s — tightest:** a new screen/graphic/text every 3–6 s (the one figure every
  source agrees on — steepest retention drop is the opening).
- **Body — cut on meaning** (new sentence/concept), ~one visual change per 15–25 s. Not a clock.
- **Every ~2–3 min — one longer "breathing" shot** (10–20 s) when an idea must sit.
- **Zooms/punch-ins:** one specific element per use, never per sentence (seasick otherwise).
- **On-screen text accent:** only the 1–3 words that matter (term/number/name), NEVER a
  duplicate of the subtitle line.
- **Meaning-inserts (смысловые вставки) — Артур's primary text layer (2026-07-26).** NOT
  full captions: selective pop-up text at key beats only (the MrBeast/Ривера pattern).
  One concise line = the POINT of what's being said («🚫 ноль программ монтажа»), an
  attention emoji, the key words in the accent colour (juicy yellow #FFD700 or brand
  green), lower-center, pop/fade-in ~0.2s, gone in 2.5–3.5s. 3–6 per minute at natural
  emphasis moments; full subtitles are usually OFF on this channel (karaoke-green if
  ever needed). Build: agent picks beats from the transcript → card (emoji+phrase+accent)
  → HyperFrames/HTML render → overlay timed to the anchor word. Never cover the speaker's
  face or what the viewer must see.
- **SFX:** 1–2 signature sounds reused (a whoosh on every cut is the amateur tell — see sound.md).
- **Memes/reactions:** only at a real joke, ~1–3 per 10 min; never a default transition.
- **J/L-cuts** are near-default for B-roll under continuous narration; **speed-ramp** waiting
  moments in demos (installs/builds/loads) instead of hard-cutting them away.

## Visual sources (voice-over: the screen must be filled continuously)

Priority — own/exact first, stock only for generic. What to use per sentence:

| Narration references… | Visual | Why |
|---|---|---|
| code / terminal / output | own screen capture (ffmpeg gdigrab / x11grab / avfoundation) | real, exact, no license |
| a specific site/product UI | browser-automation capture (Playwright) of the real site | stock never matches a named product |
| architecture / pipeline / data flow | HyperFrames or Manim diagram | precise, on-brand, anchor-word synced |
| generic cutaway (hands, server, office) | CC0 stock: Pexels / Pixabay / Coverr / NASA (API, no attribution) | free, safe to bundle in MIT |
| unfilmable abstraction | HyperFrames graphic first; AI-gen video only as last resort, disclosed | AI-slop hurts trust with a tech audience |

CC0-safe to bundle: Pexels, Pixabay, Coverr, NASA. Avoid AI-generated B-roll as a default —
YouTube penalises undisclosed synthetic media and this audience spots it fastest.

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

## Typography — the default brand «Mono»

The default design system is `assets/brand/default/brand.md` («ИИмерсивный - Mono», imported
from Claude Design). Use its fonts — do NOT pick your own:

- **Golos Text** (sans) — headlines, subtitles, body. Cyrillic-strong.
- **JetBrains Mono** — labels, meta (uppercase, wide tracking), the "typewriter" caption.
- **Playfair Display** (serif) — big numbers, names, editorial accents (used DELIBERATELY here —
  it is not an "AI default" in this system).

TTF bundled in `assets/brand/default/fonts/`. Components (subtitles A/B/C/D, lower-third,
callout, infographic) with exact specs are in `brand.md` — build them on-brand, don't reinvent.

Still-banned "AI-default" fonts (never use as a substitute): Inter, Roboto, Open Sans, Lato,
Poppins, Outfit, Sora, Nunito, Source Sans, PT Sans, Arimo. One display font per video.

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
