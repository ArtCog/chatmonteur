# ChatMonteur — Skill Index

The agent's editorial brain. Thin routers here; heavy reference material in `references/`,
loaded on demand.

| Skill | Read when | Status |
|---|---|---|
| `montage.md` | Any edit session — the pipeline orchestrator. **Holds the capability map: what exists and when to call it.** Routes mechanical vs editorial, phases ①②③ | ✅ ported |
| `cutting.md` | Removing pauses (deterministic branch) or fillers/stumbles/retakes (LLM branch) | ✅ ported |
| `hook-editing.md` | Voice and visuals recorded separately, matched by meaning (sidecar hook) | ✅ ported |
| `subtitles.md` | Building/burning captions (Netflix-grade standard, Cyrillic-aware) | ✅ standard FIXED 2026-07-26: no plate, no outline, colour accents only, karaoke default. Burn only on explicit request |
| `motion.md` | Graphics, zooms, b-roll: anchor-word sync, motion philosophy, visual-interest rules | ✅ ported |
| `sound.md` | Music beds, ducking, SFX placement (decisions; execution in references) | ✅ written |
| `production-rules.md` | Always — hard correctness rules (CFR, no stream-copy, loudnorm-last) | ✅ exists |

## References (`references/`, loaded on demand)

| Reference | Contents | Status |
|---|---|---|
| `ffmpeg-cookbook.md` | NVENC presets, micro-fades, voice chain, xfade/J-cut, overlays, Ken Burns | ✅ ported |
| `known-issues.md` | FATAL anti-patterns + warnings (the "never do this" list) | ✅ ported |
| `effects.md` | Karaoke captions (pysubs2/\kf), xfade transitions, LUT grading | ✅ ported |
| `playbooks.md` | P1–P11 operation playbooks (phrase removal, concat, overlays, oval mask…) | ✅ ported |
| `multiscene-pipeline.md` | Multi-scene assembly + LOCKED YouTube final render + concat-filter lesson | ✅ ported |
| `final-render-and-audio.md` | ONE-PASS final render, EQ-pocket + gentle duck canon, mixing levels | ✅ ported |
| `edit-sequence.md` | Why the 4-phase order is load-bearing (lock cut → geometry → color → top layers → sound → encode) | ✅ written |
| `engineering-facts.md` | **The numbers that make an edit read as professional** — ducking/mix/SFX values, cutting thresholds, rhythm & B-roll doctrine, screencast zoom table, the quality-gate scoring that blocks a boring edit, vetted libraries, interchange truths. Mined 2026-07-30 | ✅ written |
