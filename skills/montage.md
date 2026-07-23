# Montage — the pipeline orchestrator

Read at the start of ANY edit session. This skill routes the work; the specialist skills do
it. `production-rules.md` always applies.

**Default brand:** `assets/brand/default/brand.md` («ИИмерсивный - Mono») — the design system
for subtitles, lower-thirds, callouts, infographics, colours and fonts. Every on-screen element
follows it; don't invent styles.

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
   → APPROVAL → cut_edl (one pass). This is the audio "picture-lock".
   → cutting.md Tier 2

③ VISUAL MONTAGE (editorial, approval-gated) — locks the GEOMETRY, before color
   lay B-roll/screen/graphics under the narration by meaning + zooms/punch-ins +
   block-transition cards → storyboard → APPROVAL. ALL framing/zoom/placement is fixed here.
   Why before color: grade must see the final geometry; an overlay in absolute coords
   would drift/clip if a zoom lands after it.
   → motion.md + hook-editing.md

④ FINISH (one render pass, fewest encode generations)
   color grade → graphics + subtitles as the TOP layer OVER the grade → music+ducking+SFX
   → loudness −14 LUFS / true-peak LAST → single encode
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
5. **Mix test clip** (30–40 s) — levels approved before the full final render.

Everything else — executing an approved plan, excluding read-script frames, format
normalization, verification — is autonomous: do it and mention it.

## Verification (before calling anything done)

- Duration sanity: final ≈ sum of parts (catches broken concat).
- Audio by LEVEL, not duration: `volumedetect` mean_volume sane; spot-check joins.
- Loudness: −14 LUFS ±0.4; true-peak fix applied.
- Frame check: extract 2–3 frames at overlay/subtitle moments — casing, position, nothing
  important covered.

## Cost honesty

Free-local is the default (faster-whisper, auto-editor, ffmpeg, bundled assets). Before
invoking anything paid (hosted ASR), tell the user what it costs and what the free path
trades off — then let them choose.
