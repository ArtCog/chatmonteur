# ИИмерсивный — Mono (ChatMonteur default brand)

The default design system for the whole product. Imported from the creator's Claude Design
project «ИИмерсивный - Mono» (originals in `source/`). Monochrome — ink & paper.
This replaces the older «Осциллограф» (Geist/teal) system.

**Start at `catalog.json`** — every card the designer drew, what it is for, and which
component renders it. `brand-manifest.json` holds the rules on top of it (safe zones,
budgets, motion timings) and OWNS the colour values; `tokens.css` mirrors them for code,
and `build_catalog.py` fails if the two disagree. Fonts (bundled TTF): `fonts/`.

## Palette

| Token | Hex | Role |
|---|---|---|
| ink | `#0B0B0C` | near-black — text on paper, chips, inverse plates |
| paper | `#FAFAF7` | bone/off-white — text on ink, light infographic frames |
| surface | `#1A1B1D` | dark panel background |
| card-dark / card-dark-border | `#161618` / `#2A2A2C` | accent-plate card body and its hairline |
| gray-1 / gray-2 / gray-3 | `#B7B7B2` / `#8A8A85` / `#3A3B3E` | secondary / muted / faint |
| accent-hype 🔥 | `#FF5B2E` | 4px strip under accent plate E — **never text** |
| accent-danger ⚠️ | `#FFC53D` | 4px strip under accent plate N — **never text** |
| accent-insight 💡 | `#5BD1FF` | 4px strip under accent plate O — **never text** |
| caption-accent | `#FFD700` | burned-in captions only; a caption convention, not a brand accent |
| scrim | `rgba(8,9,10,.52)` | semi-transparent plate behind captions |

The green `#2BE86A` and the blue `#4C63F5` are **gone**: the refreshed brandbook is
monochrome-plus-three-signal-colours (`bank-grill-decisions-2026-08-01.md`). Colour never
carries text — it is a 4px strip under a plate, and only on elements E, N and O.

## Type

- **Golos Text** (sans) — headlines, **subtitles**, body. Excellent Cyrillic. Weights 700/800 for display.
- **JetBrains Mono** — labels, meta lines (uppercase, wide tracking), the "typewriter" caption style.
- **Playfair Display** (serif) — big numbers, names, editorial accent. Italics available.
- No other fonts. Motion is a soft ease `cubic-bezier(.33,1,.68,1)` («soft-in»), never bouncy.

## Components (exact specs from the design)

### Subtitles — 5 styles (Golos Text Bold `#FAFAF7`; NO plate, NO outline; soft drop shadow only)
⚠️ Overrides the designer source (Артур 2026-07-24, финальное): scrim plates & inversion chips
are OUT for captions. Bold white text; the key/spoken word pops by COLOUR — `yellow` `#FFD700`.
Plates/inversion stay for OTHER components (lower-third, callout) — only captions changed.

🔶 **OPEN — needs Артур.** The refreshed brandbook contradicts that decision on two points,
and captions are burned in, so guessing costs a re-render of every video:
1. Card 04 draws a scrim plate `rgba(8,9,10,.52)`; the 2026-07-24 decision removed plates.
2. Card 04 does style B's accent by **inversion** (paper chip, ink text); the 2026-07-24
   decision does it by colour. The brandbook's own rule is that colour never carries text.

Until he rules, `subtitles.py` keeps rendering exactly as it does today — the `green` option
is the only thing that must go, because that colour no longer exists anywhere in the brand.
- **A · читаем вслух** — words appear one-by-one (soft-in, ~0.2s stagger). For narrated key lines.
- **B · акцент** — the marked word in the accent colour. A single punch-word per line.
- **C · чисто** — plain line, no per-word motion. The safe default.
- **D · печатная машинка** — JetBrains Mono 500 at 23/26 of base size, typed reveal + blinking
  cursor `▌`. For "agent typing live" moments.
- **E · караоке (highlight)** — whole line visible, the word being SPOKEN takes the accent
  colour in sync. The dominant modern caption look (2026).

Geometry (fixed, from ChatMonteur standard): size ≈5.5% frame height, bottom margin ≈9%,
line width ≈80%, bottom-center anchor. See `../../../skills/subtitles.md`.

### Lower-third (plashka)
Bottom-left, design frame `left:50px; bottom:52px` — but at render scale the baseline is
**`bottom:146px`, not 135**: the card's own value puts the plate's bottom edge at y=945,
inside the manifest's playerZone (y≥934) where YouTube draws its controls. Elements 03, 20
and 43 all share 146. Light tick bar (5px `#FAFAF7`) + ink plate `#0B0B0C`,
padding 15×24. Name: **Playfair Display 600, 27px, `#FAFAF7`**. Sub: **JetBrains Mono 13px,
uppercase, letter-spacing .14em, `#B7B7B2`**. Animation: clip-reveal.

### Callout
Corner brackets (`#FAFAF7`, 3px) around the region + connector line + label plate. Label plate:
`background:#FAFAF7; color:#0B0B0C`, mono eyebrow «СМОТРИ СЮДА» + Golos 800 term. Inverse hint
plate: `background:#0B0B0C; color:#FAFAF7`, `→` + Golos 800 «важный момент». Soft scale-in.

### Infographic (light background)
Frame `#FAFAF7` with a 44px grid (`rgba(11,11,12,.05)`). Model chips inverse
(`background:#0B0B0C; color:#FAFAF7; Golos 800`). Big numbers **Playfair Display 600, up to 94px**,
`#0B0B0C`. Comparison: two columns + centered `VS` disc. Numbers big, labels small mono uppercase.

## Voice (unchanged from the channel)

Russian, «ты» not «вы», operator-pragmatic, concrete numbers, em-dash thoughts, `<em>` = accent
on a single noun. See the channel passport `_channel/CHANNEL.md`.

## Fonts license

Golos Text, JetBrains Mono, Playfair Display — all SIL Open Font License (OFL). Bundled in
`fonts/` as variable TTFs. The product code is MIT; these font files keep their OFL — see
`fonts/OFL.txt`.
