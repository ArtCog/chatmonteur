# Montage — the pipeline orchestrator

Read at the start of ANY edit session. This skill routes the work; the specialist skills do
it. `production-rules.md` always applies.

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

## The full edit pipeline (hybrid — most videos pass all three phases)

```
① SKELETON (mechanical — no content understanding needed)
   trim heads/tails → route audio branch → normalize (Branch A only) →
   silence removal PER SCENE → concat parts → working 1080p draft
   → cutting.md Tier 1 + references/multiscene-pipeline.md

② EDIT (editorial — transcript-driven, approval-gated)
   verbatim transcript of the DRAFT → intelligent cut-plan (fillers/retakes) → APPROVAL →
   EDL execution → subtitles → storyboard (anchor words) → APPROVAL → graphics per scene
   → cutting.md Tier 2 + subtitles.md + motion.md

③ FINAL (mechanical — one pass)
   1440p upscale + music/SFX/ducking + all overlays in ONE render → true-peak fix → verify
   → sound.md + references/final-render-and-audio.md + references/multiscene-pipeline.md Step 6
```

- Phase ② is optional: a clean tutorial with no fillers and no graphics ships after ① + ③.
- Never reorder: meaning cuts AFTER silence removal (a shorter transcript = less LLM work);
  music and final overlays are NEVER added before all cutting is done.
- Transcripts for subtitles/graphics come from the FINAL draft — timings drift after every cut.

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
