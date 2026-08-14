# Brand integration

ChatMonteur follows HyperFrames instead of inventing a second visual-brand
format. Every installed brand directory uses the native HyperFrames design spec:

```text
assets/brand/<name>/
├── frame.md                 visual source of truth (HyperFrames format)
├── tokens.css               runtime CSS projection of frame.md
├── components/              HyperFrames blocks and their registry metadata
├── catalog.json             generated inventory
├── usage-profiles.json      ChatMonteur's editorial mapping
├── brand-manifest.json      cue budgets and enforceable editing rules
├── channel.json             optional public channel/CTA identity
└── sound.json               optional sound policy
```

## Who owns what

- **HyperFrames `frame.md`** owns colors, typography, spacing, component
  appearance, and visual constraints.
- **HyperFrames registry items** own reusable renderable blocks.
- **ChatMonteur editorial intents** describe why a graphic is needed, independent
  of its appearance.
- **A brand's usage profiles** map those intents to that brand's components and
  priorities.
- **ChatMonteur gates** enforce density, overlap, source replacement, timing, and
  delivery quality.

The directory is packaging, not a competing brand standard. `config.toml`
selects which installed package is active:

```toml
[brand]
name = "default"
```

Changing only colors or typography should require a `frame.md`/token update and
a compatibility check, not a new editorial classification. A genuinely
different graphic language supplies different HyperFrames components and maps
the same editorial intents to them. The cutting pipeline and QC gates remain.

The bundled `default` directory is the tested Immersive Mono example. Its channel
CTA is never automatic; another publisher should replace or omit `channel.json`.
