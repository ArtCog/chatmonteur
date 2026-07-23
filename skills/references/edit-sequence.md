# Edit Sequence — why the order is load-bearing

The pipeline order in `montage.md` follows professional post-production. Each step exists so
a later step doesn't force rework or leave a visible defect. Don't reorder without reading this.

## The order and the reason for each boundary

| Stage | Comes after | Why (technical / craft) |
|---|---|---|
| Normalize (CFR + loudnorm −14) | ingest | Two jobs: clean CFR so cuts don't desync; loudnorm so the silence threshold (a fraction of peak) is valid. This is PREP loudness, not the final master loudness. |
| Silence removal (audio level) | normalize | Cuts pauses by how loud the audio is — blind to meaning but safe: a screen-demo with sound is kept. Shrinks the transcript the LLM then reasons over. |
| Transcribe | silence removal | Transcript must match the CUT timeline — timings drift after every cut, so transcribe the draft, not the raw. |
| Meaning cut (agent → cut_edl) | transcribe | The LLM decides fillers/false starts/retakes from the verbatim transcript, writes an EDL, gets approval. This locks the audio spine ("picture-lock"). |
| Visual montage: B-roll, zooms, cards | meaning cut | The visual "picture-lock". ALL geometry — placement, framing, punch-ins — is fixed here, because everything downstream depends on the final frame. |
| Color grade | visual montage | The grade must see the FINAL composited geometry to set one consistent look. Grading before a zoom lands grades the wrong framing. |
| Graphics + subtitles (top layer) | color | Kept as a separate TOP layer over the grade — never baked under it. Burning captions/graphics before the grade lets the grade tint/wash the text and defeats a fixed subtitle standard. |
| Music + ducking + SFX | graphics/subtitles | Stings/whooshes sync to graphic entrances and zoom hits — those beats must exist first. |
| Loudness −14 LUFS / true-peak | full mix | Normalizing sets a ceiling; adding audio after it clips or forces a redo. Last audio op, once. |
| Single final encode | everything | Every lossy re-encode compounds generation loss — hold a high-quality intermediate, encode to the delivery codec exactly once. |

## Voice-over specialisation

With narration (no talking head), the narration IS the assembly/rough/fine cut — those
collapse into "cut pauses in the voice + meaning cut". But the VISUAL edit still has its own
picture-lock (stage "visual montage"): B-roll/screen placement + zooms lock before color, for
the same reason a normal picture-lock exists. Captions come from the CUT narration, never the
raw. Music is mostly narration-ducking + beat-synced whooshes on graphic/zoom entrances — so
it comes after those are locked.

## Consequences if you violate the order (observed / reasoned)

- Subtitles before color → grade colours the text (tint/wash). *(Confirmed by colorist
  workflow sources.)*
- Zoom after an absolute-positioned overlay → the overlay drifts or clips. *(Reasoned from the
  "lock geometry before top layers" rule.)*
- Music/loudness before the mix is complete → clipping or a full redo.
- Multiple encodes → visible generation loss (banding, mush).

Sources: professional editing workflow guides (Frame.io, Filmsupply), Wikipedia
picture-lock / offline-online / generation-loss, O'Reilly Color Correction Handbook,
Netflix subtitle-timing spec. Full list in `Research/youtube-craft/05-video-editing/montage-upgrade/09-sequence-styles-sources.md`.
