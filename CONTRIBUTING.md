# Contributing to chatmonteur

chatmonteur grows by adding tools and pipelines — contributions welcome.

## Dev setup

```bash
git clone https://github.com/ArtCog/chatmonteur && cd chatmonteur
python -m pip install -e ".[whisper,emoji,dev]"
python -m pip install auto-editor      # silence removal backend
git config core.hooksPath .githooks    # block private files and likely secrets
pytest -q                              # fast guard tests (no ffmpeg)
```

The media smoke tests need ffmpeg on PATH:

```bash
python tests/smoke_ffmpeg.py
python tests/smoke_cut_edl.py
```

## Adding things

- **A capability (tool):** new module in `chatmonteur/tools/` exposing `TOOL`.
- **A flow (pipeline):** a YAML in `pipelines/`.

See [docs/extending.md](docs/extending.md). Tools must read everything from
`RunContext` (no hardcoded paths), write only under `ctx.paths.*`, and raise on
failure — never fail silently.

## Non-negotiables

Respect the [production-correctness rules](skills/production-rules.md): never
`-c copy` on a cut, normalize to CFR first, loudnorm last, verify audio by level,
auto-detect the encoder. These are what keep automated edits publishable.

## PRs

Keep them focused. Add/adjust a guard test in `tests/` for new logic. Credit any
third-party engine you wrap in `CREDITS.md`.
