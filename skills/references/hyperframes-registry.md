# HyperFrames registry — where brand components live

Learned 2026-07-31, after discovering the registry holds **138 ready-made blocks and
components** that this project was in the middle of rebuilding by hand. See rule zero in
`CLAUDE.md`: search here before writing anything.

## The two item kinds — the distinction is load-bearing

| | Block | Component |
|---|---|---|
| What | A standalone sub-composition: own dimensions, own duration, own timeline | An effect snippet: no dimensions, no duration |
| Installs to | `compositions/<name>.html` | `compositions/components/<name>.html` |
| Wired by | `data-composition-src` on a div in the host | pasting its HTML/CSS/JS into the host |
| Use for | title cards, lower-thirds, caption styles, VFX, charts | grain, vignette, shimmer, text treatments |

Blocks are referenced; components are inlined. A lower-third is a block. A grain overlay is
a component.

## Wiring a block into a host composition

```html
<div data-composition-id="lt-accent-underline"
     data-composition-src="compositions/lt-accent-underline.html"
     data-start="12.4" data-duration="4"
     data-width="1920" data-height="1080"
     data-track-index="1"></div>
```

`data-composition-id` **must match the block's internal id**, which must in turn match
`window.__timelines["id"]`. A mismatch renders nothing and reports no error.

## Our own components: point the registry at ourselves

`hyperframes.json` carries the registry as a URL:

```json
{ "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  "paths": { "blocks": "compositions", "components": "compositions/components",
             "assets": "assets" } }
```

Repoint it and `hyperframes add <name>` installs OUR brand items the same way. Each item is
a folder with the composition HTML plus a `registry-item.json` (name, type
`hyperframes:block` / `hyperframes:component`, title, description, tags, and — blocks only —
dimensions and duration).

## Authoring rules that are not optional

**Determinism** — the renderer seeks the timeline; anything that ignores the clock breaks:

- `gsap.timeline({ paused: true })`, always.
- **No `Math.random()`, no `Date.now()`.** Seeded PRNG (`mulberry32`) if randomness is wanted.
- Three.js draws from `tl.eventCallback("onUpdate", renderScene)` — **never** `requestAnimationFrame`.
- Cursors and decorative motion use `tl.set` at computed intervals, **not CSS animation** —
  CSS keyframes are not seekable, so they are correct in preview and wrong in the render.

**Element IDs** — every id inside a block carries a 2–3 letter prefix (`hz-cg-0`, `tw-ch-0-5`).
Blocks become sub-compositions in a shared document, and unprefixed ids collide silently.

**Captions**, from their own house rules:

- **96 px minimum** at 1080p for proportional fonts; 64–72 px acceptable for monospace.
- Readability by `-webkit-text-stroke: 2–3px` **or** multi-layer `text-shadow`.
- Call `window.__hyperframes.fitTextFontSize()` on every group or long lines overflow.
- Karaoke: `tl.to(wordEl, {...}, WORDS[wi].start)`.
- **Hard-kill every group**: `tl.set(groupEl, {opacity: 0, visibility: "hidden"}, g.end)`.
  Without it a caption lingers over the next one.
- **Never `tl.from(el, {opacity: 0})` at the same position as `tl.set(el, {opacity: 1})`** —
  the `from` clobbers the `set`. Use `tl.to`.

> ⚠️ Their 96 px is **8.9 % of frame height**; our burned-caption standard is
> `_SIZE_FRAC = 0.055` — 5.5 %, about 59 px at 1080p. Different medium (libass over the
> frame vs a web render), but Артур has already objected once that our captions look small.
> Worth measuring on real footage rather than assuming either number.

## Validation before anything ships

```bash
hyperframes lint                 # 0 errors required
hyperframes check --no-contrast  # 0 console errors required
hyperframes snapshot --at "1.0,3.0,5.0"   # visual QA without a full render
```

`check` also validates contrast — the WCAG checker item 11 of our roadmap planned to build.

## Discovery

```bash
npx hyperframes catalog --json                 # everything, machine-readable
npx hyperframes catalog --type component       # captions, overlays, text treatments
npx hyperframes catalog --tag transition
npx hyperframes add <name>                     # install one
npx hyperframes add captions                   # install every block with that tag
```

A snapshot of the catalog as of 2026-07-31 is in `_audit/hyperframes-catalog.json` (local).
Relevant to this channel: 16 `caption-*` components, 12 `lt-*` lower-thirds, 13
`transitions-*` packs, ~25 terminal themes plus `code-scroll` / `code-highlight` /
`code-typing` / `code-diff`, `data-chart`, `flowchart`, `freeze-frame-dressing`, `whip-pan`.
