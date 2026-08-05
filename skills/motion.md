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

### Is a graphic justified here? — ask the section, not the clock

Walk the script section by section and answer. A "yes" earns the graphic; nothing
earns it by elapsed time alone:

1. Is he explaining something **visual or structural**? → a diagram.
2. Is there a **number, a name or a quote** the ear can't hold? → text on screen.
3. Is there **code or a terminal**? → the real thing, captured, not described.
4. Has he been on camera **>30 s straight** with nothing changing? → the monotony
   trigger: B-roll, an overlay, or a cut to the screen.
5. Is this the **hook or the close**? → the one line that matters, large.

If none of the five fires, add NOTHING. A graphic placed to fill time is worse
than plain footage: it teaches the viewer that graphics here mean nothing.

**Placement law, once decided:** never cover the face (eyes, nose, mouth stay
visible) · pick a side (left or right) and keep it for the whole film · text
lives on screen 2–5 s — long enough to read, short enough not to feel stuck.

### Trim to the moment

A 12-second clip usually holds one 3-second moment that earns its place and 9
seconds of settling into it. Find the moment; the rest is not footage, it is
approach. Cut **before** the action's natural end — end on a look, not on the
move-off — so the cut reads as intentional rather than exhausted. Leave a few
frames of handle at both ends for the fade. Never hold on a freeze-frame: it
reads as a technical fault, not a choice.

### `overlays` — B-roll OVER the speaker (how to drive it)

The channel's b-roll style: the speaker stays in frame, the asset rides on top. You source
the asset (own capture / Playwright screenshot at `device_scale_factor=2` for sharpness /
CC0 stock), write `projects/<name>/transcripts/overlays.json`, get the storyboard approved,
then call the `overlays` capability:

```json
{"overlays": [
  {"start": 15.0, "end": 20.5, "file": "assets/github.png",
   "pos": "top_right", "width": 0.46}
]}
```

- `pos`: `top_right` / `top_left` / `top_center` / `center_right` / `center_left` — the
  safe zone is the upper half and sides; the lower center belongs to captions/inserts
  (the tool refuses anything else). PICK THE SIDE AWAY FROM THE SPEAKER'S FACE — check a
  frame first; face-safe automation is future work.
- `width`: fraction of frame width, 0.1–0.7 (default 0.45); bigger would bury the speaker —
  cut away instead of overlaying.
- `file`: image (looped) or video clip (played muted from its start). 5–20 s per overlay,
  in/out on meaning boundaries; J/L-feel comes from the alpha fade built into the tool.

### `zooms` — how to drive it (Артур 2026-07-26: `punch` is the channel standard)

You pick the emphasis moments from the FINAL-cut transcript, write
`projects/<name>/transcripts/zooms.json`, show the plan, then call the `zooms` capability:

```json
{"zooms": [
  {"start": 34.2, "end": 37.8, "kind": "punch", "scale": 1.15, "reason": "story"},
  {"start": 61.0, "end": 66.5, "kind": "push",  "scale": 1.10, "reason": "emotion"}
]}
```

- Kinds: **`punch`** (instant in/out — reads as an angle change; THE DEFAULT) · `ease`
  (soft 0.35s) · `push` (slow creep for a long thought) · `drift` (punch + slow +3%).
- **`reason` — name why the move exists**, from Murch's Rule of Six in the order he
  weights them: `emotion` (51%) · `story` (23%) · `rhythm` (10%) · `eye_trace` (7%) ·
  `plane` (5%) · `continuity` (4%). The storyboard review says so out loud when a move
  rests only on the bottom three — following movement is the weakest reason to push in.
  It advises, never blocks; but if you cannot name a reason, the zoom is decoration.
- `scale` defaults to 1.15 (emphasis); 1.3 only for a critical point. >1.3 on a 1080p
  source visibly softens — the honest fix is recording at higher resolution.
- Centre defaults to (0.5, 0.40) — a talking-head face sits above frame centre. Windows
  must not overlap (their scales would add; the tool refuses).
- Engine notes (learned on real footage): zoompan's clock is **`in_time`** (`t` does not
  exist there), and the chain upscales 2× before zooming — zoompan crops in whole pixels
  and slow moves stutter at 1× (the documented anti-jitter cure).
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
- **Screencast has a tighter clock than talking head.** Procedural video is watched
  2–3 minutes regardless of its length (Guo/Kim/Rubin, 6.9M edX sessions) — a flat line
  a lecture doesn't share. So a screen-recording stretch needs a real RESET every ~2.5 min:
  a cut to camera, a chapter card, a graphic. **A zoom is not a reset** — same screen,
  closer. Declare `"material": "screencast"` at the top of the storyboard and the plan
  gate holds you to it (talking-head material keeps the looser 90 s dead-air rule).
- **Zooms/punch-ins:** one specific element per use, never per sentence (seasick otherwise).
- **On-screen text accent:** only the 1–3 words that matter (term/number/name), NEVER a
  duplicate of the subtitle line.
- **Meaning-inserts (смысловые вставки) — Артур's primary text layer (2026-07-26, LOCKED).**
  NOT full captions: selective pop-up text at key beats only (the MrBeast/Ривера pattern).
  **STANDARD look = «эмоджи сверху»**: attention emoji above (~135px @1080), below it ONE
  concise line = the POINT of what's said («🚫 ноль программ монтажа»), Golos 800 ~96px
  white, key words in juicy yellow `#FFD700`, no plate, soft shadow, lower-center,
  fade/pop-in ~0.2s, gone in 2.5–3.5s. Alt look «стикер» (white rounded chip, ink text) —
  ONLY when Артур asks. **ONE TEXT LAYER AT A TIME** — an insert and a motion-graphic scene
  must never share screen time (Артур 2026-07-30). Declare motion windows in the storyboard's
  `motion` section; the `storyboard` tool refuses the clash. Both use VIDEO-LOCAL seconds: if
  a HyperFrames composition offsets the video (`data-start` > 0) its clock differs, and that
  timebase mix silently misplaces graphics — keep video at `data-start="0"` and make a title
  card a SEPARATE clip concatenated in front.
  **The HOOK gets 1–2 inserts MANDATORY**; body — by meaning or on
  request. Full subtitles are OFF unless Артур explicitly says «добавь субтитры»
  (then karaoke-yellow). WHEN: inserts are built in phase ③ VISUAL MONTAGE, together with
  the rest of the motion pass — after the meaning cut locks timing, before color.
  Build: agent picks beats from the FINAL-cut transcript → writes `inserts.json` → shows
  the list for APPROVAL → calls the `inserts` capability. Never cover the speaker's
  face/hands or what the viewer must see (face-safe-zone).

### `inserts` — how to drive it

The tool is the hands; YOU choose the beats, condense the thought, pick the emoji and the
key words. Write `projects/<name>/transcripts/inserts.json`:

```json
{"inserts": [
  {"start": 5.5, "end": 8.8, "emoji": "🚫",
   "text": "ноль программ монтажа", "key": "ноль программ"}
]}
```

- `text` — ONE short line, the POINT of what's being said (≤28 chars/line, wraps beyond).
  Not a transcript quote — the condensed thought.
- `key` — the substring to accent (optional; must appear in `text` or it's drawn plain).
- `emoji` — optional; picked for attention, matching the emotion (🚫 danger/negation,
  ✅ result, ⚠️ warning, 💰 money, 🔥 hot take).
- Params: `style` = `emoji_top` (LOCKED default) | `sticker` (ONLY when Артур asks),
  `accent` = `yellow` (единственный цвет субтитров/вставок).
- Timing: 2.5–3.5 s per insert, landing ON the anchor word, 3–6 per minute max.

**Colour emoji are PNG overlays, not font glyphs** — libass renders outline glyphs only, so
a COLR/CBDT emoji comes out grey through `ass=` (verified on a real frame 2026-07-26). The
tool draws them with Pillow (`pip install chatmonteur[emoji]`); without Pillow the insert
still burns, just text-only.
- **SFX:** 1–2 signature sounds reused (a whoosh on every cut is the amateur tell — see sound.md).
- **Memes/reactions:** only at a real joke, ~1–3 per 10 min; never a default transition.
- **J/L-cuts** are near-default for B-roll under continuous narration; **speed-ramp** waiting
  moments in demos (installs/builds/loads) instead of hard-cutting them away.

## Visual sources (voice-over: the screen must be filled continuously)

**Classify BEFORE you source.** For every meaning-bit of the transcript, first decide what
KIND of statement it is — only then pick the source row below. Skipping this step degrades
every resolver into "insert something by keyword", which is exactly the visual Артур called
out as amateur:

1. **Named entity** (a product, a model, someone's post) → the REAL thing: live screenshot.
2. **Abstraction** (how it works, comparison, numbers) → OUR graphic (HyperFrames, on-brand).
3. **Demonstration** (I did X, it looked like this) → the actual screencast footage.
4. **Connective / emotion** (transitions, jokes, asides) → cutaway or meme, sparingly.
5. **None of the above fits** → AI-gen, last resort, disclosed.

**Артур's anchors beat inference.** Before planning, ask him what to show at the 3–5 moments
that matter most; his ten minutes outrank an hour of guessing. Everything else is sourced by
the rules above.

### The motion floor — no DEAD static (Артур 2026-07-31; scoped 2026-07-31)

Drama/shorts channels fill every gap with background gameplay; the data behind the trick is
real even though the form is wrong for us: continuous on-screen motion holds **1.5–2× the
engagement time** of static holds (edX study, p ≪ 0.001, in
`references/engineering-facts.md`). **The same study's second finding scopes the rule**:
on slides/code, learners deliberately PAUSE on static holds to read — a hold on content the
viewer must study is a feature, not dead air. So:

- **STORY sections (hook, narrative, connectives): no static second.** Every gap gets motion.
- **TEACH sections (code, a diagram, a config the viewer reads): a deliberate static hold is
  legitimate** — and per Артур's standing rule, no decoration on top of what must be read.
  Dead static = a frozen frame nobody is supposed to be studying. THAT is banned everywhere.
- **Filler priority: thematic first, gameplay allowed** (Артур 2026-07-31: «будем, как в
  том референсе, использовать где-то видеоигру на фоне»). Thematic motion — a running
  terminal, an agent typing, the discussed tool's UI — carries meaning while it moves, so
  it is the default. Background gameplay is a legitimate deliberate choice for story
  sections; which one a given stretch gets is Артур's call at the storyboard gate. Both
  live in the asset bank.
  **Confirmed on real frames 2026-08-04.** Артур looked at gameplay next to an authored
  abstract loop and picked gameplay outright: the loop read as boring, the game did not.
  So gameplay is a first-class background here, not a grudging exception — and generating
  an abstract loop ourselves is NOT the answer (that attempt was dropped the same day).
  Two things that DO hold from the test:
  - **Under a card it must be dimmed**, which `overlays` now does automatically. A
    blurred-only game backdrop still read as sky-blue and orange against a black-gray brand.
  - **Licence is checked, never assumed.** Even a free game's footage came under
    CC BY-SA 4.0, whose share-alike reaches the video around it; a stranger's
    "no-copyright" claim is worth nothing. Record the real licence in the ledger.
- **Evidence cards sit on a blurred AND DIMMED live backdrop**: when showing a
  screenshot/chat/post, the background is the moving video (or thematic filler), never a
  flat colour — but blurred, darkened and desaturated, all three. Blur removes detail;
  only the dimming removes WEIGHT. `overlays` does this automatically for
  `backdrop: "blur"`; the numbers live in `overlays.py`. The motion floor holds even
  while the viewer reads.
- Static images that must appear get Ken Burns (`zooms`/`overlays`) — minimum drift, never
  a frozen frame.
- The `storyboard` gate already refuses >90 s without a visual event; this rule is stricter:
  the GAPS between events must themselves move.

### Breathing, cards and the dark discipline (reference: «вайбкодер», ×37 reach)

Full breakdown: `Research/youtube-craft/05-video-editing/ai-montage-landscape-2026-07-31.md`.
⚠️ **Status: hypotheses from ONE reference video** (n=1, entertainment format, not our
genre). Consistent with the pacing research, but each pattern must survive a dogfood run
on Артур's own footage before it hardens into canon. The three candidates:

- **Breathing, not a constant rate.** On PROOF sections (screens, chats, UI) the picture
  changes every 5–10 s; on pure storytelling the editor deliberately lays ONE unbroken
  filler stretch of 30–60 s with zero cuts. Do not chop filler to hit a cuts-per-minute
  number — the alternation IS the rhythm.
- **Evidence card** (`overlays`: `card: true` + `backdrop: "blur"` + `pos: "center"`):
  every screenshot — Telegram, Finder, a tweet — becomes the SAME rounded-shadowed card
  over the blurred live layer. One style for all sources is what makes pasted material
  read as a designed video. The reference spends 4–6 manual hours on ~15–20 such cards;
  ours is one plan line each.
- **«Затемни то, что не главное» beats a LUT.** Their colour unity: dark theme in every
  app shown + the filler layer dimmed and blurred whenever it is background, full
  contrast only when it IS the shot. Source discipline, not grading — matches our
  ungraded default and completes it.

Frame device worth keeping: full-screen film-style plates (black, centered white text)
as intro/outro — «основано на реальных событиях» → «продолжение следует». We have the
title-card composition for this; it is a brand-book component candidate.

### Sourcing the material — two beats, and who does which (Артур 2026-08-01)

Decisions from the bank grill; the reasoning is in `bank-grill-decisions-2026-08-01.md`.

**Two beats, never one.** The list of material needed is born on the SCRIPT (the planning
canvas): what to film, what to download, what to generate — so the bank and the project's
`assets/` fill up before or during the shoot. The exact placement against timecodes happens
only AFTER the final cut, because every cut moves everything. Planning placement early is
work thrown away.

**The sourcing mode has a default — state it, don't interrogate.** A ritual "which mode
are we in?" every single video trains him to stop reading the question. So: assume the
default, say in one line which mode you are working in, and ASK only when you want to
deviate (you think you can do this one alone, or you need more from him than usual).

- **Default: Артур takes part** in choosing the meaningful screenshots. Full autonomy
  only when he grants it for this video.
- **Annotating what was found is ALWAYS the agent** — highlighting the sentence in the
  article, circling the UI element.
- **Social networks (X, Telegram): screenshots come from Артур.** Playwright hits login
  walls and bot checks there; do not burn an hour proving it again.
- **Never substitute motion graphics for a real screenshot.** Graphics are for abstractions;
  a NAMED entity gets the real thing (the classification table below already says this).

### The asset bank

Channel-wide reusable material lives in `bank/` at the repo root (contents gitignored —
weight + third-party licences; only the spec `bank/BANK.md` is committed): gameplay /
thematic / illustrations / screenshots / music, each file registered in `ledger.jsonl`
(what, source, license, `used_in`). Before picking an asset, CHECK `used_in` — similar
shots must not repeat across videos (Артур's standing rule). After burning an asset into
a video, append the video slug to its `used_in`. Per-video assets stay in the project's
`assets/`, not in the bank.

**The agent NEVER picks the background alone — it ASKS.** Артур 2026-08-04: «агент же
будет меня спрашивать, а не сам выбирать, не так ли? По умолчанию так должно быть».
So at every stretch that needs filler, offer the candidates from the ledger — his
`priority` order, the `tier` that fits the section — and let him choose. Autonomy here
is something he grants later and per video, never something the agent assumes. The
`used_in` check still applies on top: do not offer a clip that already carried a video.

**Two registries, not two competitors.** `manifest.json` (written by `stock` into the
project) is the RAW catch — it lives and dies with the video, and is not to be rewritten.
`ledger.jsonl` in the bank is the PERMANENT registry, and holds only what was promoted.
Promotion = a line in the ledger plus the file moved, and it happens on a deliberate
decision — when the thing has actually proved reusable (logos, model covers, a recurring
metaphor). One-off material never gets dumped into the forever pile.

Priority — own/exact first, stock only for generic. What to use per sentence:

| Narration references… | Visual | Why |
|---|---|---|
| code / terminal / output | own screen capture (ffmpeg gdigrab / x11grab / avfoundation) | real, exact, no license |
| a specific site/product UI | browser-automation capture (Playwright) of the real site — on this machine Playwright lives in `C:/Users/magme/AppData/Local/Programs/Python/Python313/python.exe`, NOT the PATH python | stock never matches a named product |
| architecture / pipeline / data flow | HyperFrames or Manim diagram | precise, on-brand, anchor-word synced |
| generic cutaway (hands, server, office) | **`stock` capability**: Openverse (keyless) / Pexels / Pixabay — fetches candidates + license manifest; YOU look at every candidate and score 1–5 (relevance/resolution/style/POV), reject and re-query freely | free; CC-BY needs the credit from `manifest.json` in the description |
| meme / reaction | **`stock` capability**, `kind="meme"` (Imgflip top-100 templates, keyless) | free |
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
from Claude Design). **The brand is BLACK-GRAY MONOCHROME (ink `#0B0B0C` / paper `#FAFAF7` /
grays)** — colour is a SMALL accent, never the base of a composition (Артур
2026-07-26: «наш бренд чёрно-серый»). Motion graphics live in that monochrome world.
Use its fonts — do NOT pick your own:

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
