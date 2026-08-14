# Motion graphic selection guide

This is the human entry point for choosing the default brand's motion graphics.
It answers **why, where, and how often** a graphic may be used. It does not
replace the visual specifications.

## Sources of truth

1. `usage-profiles.json` owns the editorial profile for every one of the 68
   designer cards: role, priority, eligible sections, source treatment, positive
   trigger, negative trigger, and decision basis.
2. `catalog.json` is the generated inventory. `build_catalog.py` merges the
   editorial profile into every card as `card.editorial` and fails if any card
   lacks a profile.
3. `frame.md` owns visual design and safe zones; `tokens.css` is its checked
   runtime projection.
4. `brand-manifest.json` owns enforceable cue timing and density budgets. It
   does not decide which graphic serves a sentence.
5. `components/<name>/` owns the renderable HyperFrames implementation.

Never choose by card number or appearance alone. Start from the spoken beat and
the editorial job.

## Selection order

1. Read the final-cut transcript and identify the exact spoken beat.
2. Name the editorial job: agenda, enumeration, warning, insight, shortcut,
   source citation, comparison, chapter boundary, and so on.
3. Look up candidates by `editorial.role` in `catalog.json`.
4. Prefer `preferred` when its trigger is present. Use `situational` only when it
   adds information. `explicit-only` requires Artur's direct request or approval.
   Never use `unavailable`; ask before using `review-needed`.
5. Check `sourceTreatment`. `replaces-source` is an editorial decision to hide
   useful footage, never a technical default. Anything that interrupts useful
   footage requires approval.
6. Align the entrance to the matching word or phrase in the final transcript.
   A list item begins on its own spoken cue, not on a decorative fixed stagger.
7. Enforce the one-text-at-a-time and accent-budget gates.

## Confirmed list language

| Treatment | Job | Section | Priority | Rule |
|---|---|---|---|---|
| `agenda-light-chips` prototype | Preview 3–5 things the viewer will get | Hook | Preferred when a spoken agenda exists | Light is the default theme; preserve the source in a true split; reveal each item on its transcript cue |
| `process-rail-light` prototype | Make an in-body enumeration easier to follow | Body | Situational | Large outlined numbers; preserve the source; use only when the spoken steps benefit from remaining visible |
| `19` original | Full-frame process steps | Body | Situational | Requires approval because it replaces useful footage |
| `33` | Real YouTube chapter index | Hook or outro | Situational | Display only meaningful real timecodes; never fake them for decoration |
| `40` | Voice-free kinetic stack | Intro or chapter boundary | Explicit-only | Never compete with narrated agenda timing |
| `12·A` | Full-frame thesis list | Hook or body | Explicit-only | Use only when the list must become the sole visual |

## Confirmed accent language

| Treatment | Editorial job | Priority |
|---|---|---|
| `N ⚠️` | Main important thought, rule, takeaway, or warning | Preferred; primary accent treatment |
| `O 💡` | Real insight or realization | Preferred when the beat is genuinely an insight |
| `E 🔥` | One of the strongest/high-energy moments | Preferred only for the few strongest beats |
| `L` | Short path, version, caveat, or aside | Preferred when the aside adds information |
| `M` | Longer supporting context | Situational; never duplicate narration or hide actionable UI |

## Complete priority index

This index covers all 68 designer cards. Search the ID in `catalog.json` for its
exact role and positive/negative trigger.

- **Preferred:** `20`, `25`, `28`, `29`, `E`, `L`, `N`, `O`.
- **Situational:** `03`, `05`, `06·A`, `06·B`, `13·A`, `13·B`, `15`, `16`,
  `17`, `18`, `19`, `21`, `23`, `24`, `26`, `27`, `31`, `33`, `34`, `35`,
  `36`, `41`, `43`, `44`, `A`, `B`, `C`, `F`, `H`, `I`, `J`, `K`, `M`.
- **Explicit-only:** `01`, `02·C`, `02·D`, `04`, `07·A`, `07·B`, `10`,
  `10·B`, `12·A`, `32`, `37`, `38`, `39`, `40`, `42`.
- **Review needed:** `08`.
- **Unavailable:** `02·A`, `02·B`, `07·C`, `07·D`, `09`, `11`, `12·B`,
  `12·C`, `14`, `D`, `G`.

These priorities are expected to sharpen through real-video review. Change the
profile when Artur makes a decision, then rebuild the catalog and run the tests;
do not leave the decision only in chat or a dogfood note.
