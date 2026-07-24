# ИИмерсивный — Mono (ChatMonteur default brand)

The default design system for the whole product. Imported from the creator's Claude Design
project «ИИмерсивный - Mono» (originals in `source/`). Monochrome — ink & paper — with one
green accent. This replaces the older «Осциллограф» (Geist/teal) system.

Tokens: `tokens.css`. Fonts (bundled TTF): `fonts/`. Agents read THIS file to render captions,
lower-thirds, callouts and infographics on-brand.

## Palette

| Token | Hex | Role |
|---|---|---|
| ink | `#0B0B0C` | near-black — text on paper, chips, inverse plates |
| paper | `#FAFAF7` | bone/off-white — text on ink, light infographic frames |
| surface | `#1A1B1D` | dark panel background |
| gray-1 / gray-2 / gray-3 | `#B7B7B2` / `#8A8A85` / `#3A3B3E` | secondary / muted / faint |
| accent | `#2BE86A` | Mono-green — one accent per moment, never a wash |
| info | `#4C63F5` | blue — rare semantic only |
| scrim | `rgba(8,9,10,.52)` | semi-transparent plate behind captions |

## Type

- **Golos Text** (sans) — headlines, **subtitles**, body. Excellent Cyrillic. Weights 700/800 for display.
- **JetBrains Mono** — labels, meta lines (uppercase, wide tracking), the "typewriter" caption style.
- **Playfair Display** (serif) — big numbers, names, editorial accent. Italics available.
- No other fonts. Motion is a soft ease `cubic-bezier(.33,1,.68,1)` («soft-in»), never bouncy.

## Components (exact specs from the design)

### Subtitles — 4 styles (Golos Text Bold `#FAFAF7`; plate = scrim `rgba(8,9,10,.52)`, padding 7/26 em, soft-in)
- **A · читаем вслух** — words appear one-by-one (soft-in, ~0.2s stagger). **NO plate** —
  Артур 2026-07-24: динамичные стили жгутся чистым текстом (в макете плашка была, решение сильнее макета).
- **B · акцент** — one word inverted: SOLID `background:#FAFAF7; color:#0B0B0C`. Emphasis by
  INVERSION, not colour. On plate.
- **C · чисто** — plain line, no per-word motion. On plate. The default.
- **D · печатная машинка** — JetBrains Mono 500 at 23/26 of base size, typed reveal + blinking
  cursor `▌`. **NO plate** (same rule as A). For "agent typing live" moments.

Geometry (fixed, from ChatMonteur standard): size ≈5% frame height, bottom margin ≈9%,
line width ≈80%, bottom-center anchor. See `../../../skills/subtitles.md`.

### Lower-third (plashka)
Bottom-left (`left:50px; bottom:52px`). Light tick bar (5px `#FAFAF7`) + ink plate `#0B0B0C`,
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
