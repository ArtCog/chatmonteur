# Montage — the pipeline orchestrator

Read at the start of ANY edit session. This skill routes the work; the specialist skills do
it. `production-rules.md` always applies.

**Active brand:** read `[brand].name` from `config.toml` (fallback: `default`),
then use `assets/brand/<name>/frame.md` as the visual source of truth and that
pack's `usage-profiles.json` for editorial selection. Every on-screen element
follows the active pack; don't invent styles.

## Every capability, and when to reach for it

A capability you don't remember exists is a capability the project doesn't have. Only
`normalize · cut_silence · transcribe · color · subtitles · render · qc` run from the
`talking_head` pipeline; **everything else you call yourself.** That is by design — those
steps need your judgement — but it means forgetting this table is exactly how a session ends
with "he just cut the pauses and added subtitles".

| Capability | Call it when | Phase |
|---|---|---|
| `normalize` | always first — VFR/odd input → clean CFR | ① |
| `cut_silence` | remove pauses by audio level, per scene | ① |
| `transitions` | joining separate pieces: title card + body, several takes, intro/outro. Three kinds, one primary on ≥60 % of joins or it refuses | ① |
| `transcribe` | before any editorial decision | ② |
| `cut_edl` | execute an APPROVED meaning cut | ② |
| `redact` | permanently cover credentials, personal data, or private UI found during source review; solid cover, never reversible blur | ② |
| `stock` | source a free, commercially-safe image/clip before storyboarding | ③ |
| `motion` | render a brand component to transparent ProRes 4444 for compositing | ③ |
| `cues` | burn a brand cue list (`{t, element, text}`, see the manifest's `cueFormat`) — checks it against the brandbook's budgets first; `dry_run` holds the gate without rendering | ③ |
| `contact_sheet` | the visual gate itself: renders the plan as ONE scrollable HTML page — picture + the words it covers + timecode. Show THIS, never raw JSON | ③ |
| `storyboard` | ONE call executing the approved visual plan (zooms → overlays → inserts). **Scores the plan and refuses a thin one** | ③ |
| `zooms` `overlays` `inserts` | individually only when iterating on one layer; normally go through `storyboard` | ③ |
| `color` | grade before any text layer burns | ④ |
| `subtitles` | only when the user asks for captions; ASK which variant first | ④ |
| `sound` | music bed + sidechain ducking + SFX. **The layer that most separates an edit from a cut** — reach for it, it is not optional polish | ④ |
| `render` | final encode, loudness last | ④ |
| `qc` | last. Blocks a broken file; never work around it | ④ |

## External skills — which one to OPEN at each step

Our capabilities execute; these skills carry the knowledge of the engines underneath. The
lesson behind this table: 8 HyperFrames skills sat installed on this machine while graphics
were being hand-written from memory. If a step below names a skill, open it BEFORE working —
that is what "the agent follows instructions, not invention" means in practice.

| When | Open (Skill tool / `~/.claude/skills/`) | It owns |
|---|---|---|
| Any graphics work at all | `hyperframes` | the entry point: project state, routing to the right workflow |
| Writing/editing a composition | `hyperframes-core` | the composition contract: `data-*` timing, clips, variables, determinism |
| Installing/wiring brand components | `hyperframes-registry` (+ our `references/hyperframes-registry.md`) | catalog, add, block vs component, pointing the registry at our items |
| Choosing motion for a graphic | `hyperframes-animation` | motion rules, blueprints, GSAP/keyframe adapters |
| Brand/style decisions in a composition | `hyperframes-creative` | palettes, typography, design-spec handling |
| Rendering, validating, snapshots, beats | `hyperframes-cli` | every command: check, lint, snapshot, compare, beats, batch |
| Sourcing music / SFX / images / LUTs | `media-use` | one `resolve` verb → frozen local file + licence ledger; TTS, captions, background removal |
| OBS / recording questions | `obs-studio` (user skill) | Arthur's recording setup |
| Mechanical ffmpeg outside our tools | `video-montage` (user skill) | the C:\MONTAGE workspace canon |

## Step 0: classify the task — don't grab the first tool

**The boundary question: do you need to understand the CONTENT to decide where to cut?**

- **No → mechanical.** Exact operations named: "cut 1:20–1:45", "remove silence", "concat
  these", "burn subtitles", "add overlay", "color grade", "render". → `cutting.md` Tier 1,
  `references/playbooks.md`, `references/ffmpeg-cookbook.md`.
- **Yes → editorial.** "Make a video out of this raw footage", remove fillers / false starts
  / bad takes by meaning, motion graphics, hook assembly. → `cutting.md` Tier 2,
  `motion.md`, `hook-editing.md`. Requires transcription.
- **Unclear** ("process this video") → **ASK: mechanical cleanup or full edit?** Never
  silently default to mechanical.
- Voice and visuals recorded SEPARATELY, matched by meaning → `hook-editing.md`.

## The intake — ONE batch of questions before any work (Артур 2026-07-31)

For a full edit, ask everything upfront in a single message — not one question per phase.
Deterministic list, skip only what the request already answered:

1. **Footage type** — talking head / screencast / both? (routes the zoom table and pacing)
2. **Cut depth** — pauses only (mechanical), or intelligent (fillers, retakes, restructure)?
3. **Anchors** — what must the viewer SEE at the 3–5 key moments? (his 10 minutes beat an
   hour of my guessing — see motion.md)
4. **Captions** — none by default; burn only if he says so (then variant `highlight`+yellow
   is already locked).
5. **Music** — mood, or none? SFX on cuts?
6. **Target** — runtime and deadline; anything to definitely NOT cut?

Answers land in the project's `PLAN.md` so a resumed session doesn't re-ask.

## The full edit pipeline (four phases; order is load-bearing)

The order below is not arbitrary — it follows professional post-production (lock the cut →
lock the geometry → color → topmost layers → sound → one encode). Each rule prevents rework
or a visible defect; the "why" is in `references/edit-sequence.md`.

```
① SKELETON (mechanical — no content understanding needed)
   trim heads/tails → route audio branch → normalize (CFR + loudnorm −14, Branch A) →
   silence removal by AUDIO LEVEL, per scene → concat parts → working draft
   → cutting.md Tier 1 + references/multiscene-pipeline.md

② MEANING CUT (editorial — transcript-driven, approval-gated) — locks the audio spine
   verbatim transcript of the DRAFT → intelligent cut-plan (fillers/false starts/retakes)
   → APPROVAL → cut_edl (one pass) → inspect real frames for credentials/private data
   → redact before any review copy leaves the project. This is the audio "picture-lock".
   → cutting.md Tier 2

③ VISUAL MONTAGE (editorial, approval-gated) — locks the GEOMETRY, before color
   FIRST ask who sources the material for this video (agent alone / Артур supplies
   links and screenshots / split) — the default is that he takes part, and social-
   network screenshots always come from him (motion.md, «Sourcing the material»).
   THEN classify every meaning-bit (entity / abstraction / demo / connective —
   motion.md) and source its visual: live screenshot, HyperFrames graphic, own
   screencast, stock, evidence card (`card`+`backdrop:"blur"`). Enforce the motion
   floor: no static second; connective gaps get thematic filler with BREATHING
   (30–60 s unbroken is right on pure storytelling). Then plan the whole pass as
   ONE artifact — `transcripts/storyboard.json` with `zooms` + `overlays` +
   `inserts` sections → render it with `contact_sheet` and show THAT page (one
   candidate per slot; every bank-filler beat carries a `why`) → APPROVAL, and a
   second round only on the beats marked wrong → ONE call to the `storyboard`
   capability, which burns in the load-bearing order: zooms (geometry locks) →
   overlays (placed on final geometry) → inserts (text on top). 1–2 inserts in
   the hook MANDATORY. Motion-graphic clips (HyperFrames components from the
   brand registry) render via `motion` with alpha and are placed as overlays or
   concatenated as their own clips — declare their windows in the `motion`
   section so the one-text-at-a-time check sees them.
   → motion.md + hook-editing.md + references/hyperframes-registry.md

④ FINISH (one render pass, fewest encode generations)
   transitions between blocks (hard cut default; crossfade/fade only where the
   decision tree says — transitions.py enforces the 60 % primary discipline) →
   color grade (UNGRADED default; unity comes from dark-source discipline, not a
   LUT) → graphics + subtitles as the TOP layer OVER the grade → music+ducking+SFX
   (sound.py: bed −20 dB, sidechain duck, speech-band notch; SFX lands 15 ms early)
   → loudness −14 LUFS / true-peak LAST → single encode → `qc` gate blocks a
   broken file
   → sound.md + references/final-render-and-audio.md + references/multiscene-pipeline.md Step 6
```

- Phases ②③ are optional: a clean tutorial with no fillers and no graphics ships after ① + ④.
- **Subtitles/graphics burn AFTER color, never before** — grading colours the caption pixels
  otherwise (tints/washes the text, breaks the subtitle standard). They are a top layer.
- **Geometry (B-roll placement, zooms) locks BEFORE color** — grade the frame the viewer
  actually sees.
- Meaning cut AFTER silence removal (shorter transcript = less LLM work); music and final
  overlays NEVER before all cutting is done.
- Transcripts for subtitles/graphics come from the FINAL draft — timings drift after every cut.
- Style target for pacing/graphics: educational-explainer + Fireship density, NOT MrBeast
  overstim — see motion.md. Visual sources: own screen-capture / browser shots / HyperFrames
  first, CC0 stock (Pexels/Pixabay/Coverr/NASA) for generic cutaways — see motion.md.

## Approval gates (never render past one silently)

1. **Cut-plan** (Tier 2 meaning cuts) — every removal listed with timestamp, quote, reason.
2. **Voice tempo** (hook editing) — before any visuals.
3. **Storyboard** (graphics) — beats + anchor words + animation types.
4. **Overlay wording** — exact strings confirmed (ASR mishears; burned typos cost a re-render).
5. **Subtitle variant** — which of the four brand styles (clean / read_aloud / accent /
   typewriter) fits this video. Propose the fittest, ASK before burning. → `subtitles.md`.
6. **Mix test clip** (30–40 s) — levels approved before the full final render.

Everything else — executing an approved plan, excluding read-script frames, format
normalization, verification — is autonomous: do it and mention it.

## Two gates that refuse (they are not advisory)

Approval gates ask the user. These two ask the work, and stop the pipeline.

- **`storyboard` scores the plan** before a frame burns: >90 s with no visual event, text on
  screen >60 % of the runtime, repeated captions, three identical zooms in a row. Fix the plan;
  `allow_thin=True` only when plain footage is genuinely right.
- **`qc` scores the file** last: black frames at 10/35/65/90 %, silence, clipping, missing
  streams, >25 % duration drift. Evidence in the sibling `<artifact>.qc.json`.

When either fires, **never re-run with the check disabled.** Fix what it names.

## Write plans in causes, never in moods

A plan is an instruction to a later stage, and mood words instruct nothing: "epic
reveal", "moody atmosphere", "powerful swell" mean something different to every
reader and cannot be executed or checked. Name the concrete cause that would
produce the feeling instead:

| Instead of | Write |
|---|---|
| «эпичное появление» | wide pull-back, subject against the light, 8 s hold |
| «мощный акцент музыки» | music drops at 0:42, 1.5 s of silence, returns at half tempo |
| «динамично» | cut every 3–5 s, three shot sizes, no repeat |

The word **«cinematic» is banned outright** — it names a feeling and hides the
decision. Every gate in this project scores what a plan *says*; a plan written in
adjectives passes them while meaning nothing, which is the one failure mode the
gates cannot catch for you.

## Verification (what qc does NOT cover)

`qc` already checks duration drift, silence, clipping and black frames. What still needs eyes:

- Loudness: −14 LUFS ±0.4 (qc checks for clipping, not for target).
- Frame check at overlay/subtitle moments — casing, position, nothing important covered.
- Spot-check the audio at joins after a `transitions` run.

## Cost honesty

Free-local is the default (faster-whisper, auto-editor, ffmpeg, bundled assets). Before
invoking anything paid, verify that a real capability adapter is installed, tell the
user what it costs and what the free path trades off, then let them choose. Possible
paid extension points include hosted ASR; v0.1 does not ship one.

The paid slots that do exist in the broader workflow:
- **AI illustrations** (Nano Banana Pro ~$0.04/img, Ideogram ~$0.06 — both handle Cyrillic
  text in-image) — ONLY for the "nothing-fits" row of the source table (motion.md): a
  metaphor that can't be filmed, screenshotted, or drawn as a brand graphic. Fixed
  style-prompt per video so illustrations stay consistent; disclose synthetic media where
  YouTube's rules require it.
