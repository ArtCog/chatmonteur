# Bundled sound pack

This is the small publication-safe fallback used by `skills/sound.md` when a
project does not provide its own licensed music and effects. It is deliberately
minimal: one neutral background loop and one UI accent, both redistributable
under CC0 1.0.

## Inventory

- `music/simple-loop.ogg` — calm two-minute background loop by polosik.
- `sfx/ui-hover.mp3` — short UI hover/selection accent by SRG774.

`ledger.jsonl` is the machine-readable authority for creator, primary source,
licence, duration, and SHA-256. Every audio file in this directory must have
exactly one ledger entry; the release-boundary test enforces that invariant.

CC0 does not require attribution. The creator and source are still retained in
the ledger for provenance and optional credits.
