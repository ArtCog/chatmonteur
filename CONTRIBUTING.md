# Contributing to ChatMonteur

Thanks for helping make agent-driven video editing more reliable. Bug reports,
documentation fixes, focused feature proposals, and tested pull requests are
welcome.

## Before opening an issue

- Search existing issues first.
- Use the bug form for reproducible failures and the feature form for new
  capabilities or workflow changes.
- Remove API keys, personal paths, private footage, transcripts, and licensed
  media from logs and examples.
- Report suspected vulnerabilities through the private process in
  [SECURITY.md](SECURITY.md), not through a public issue.

## Local development

ChatMonteur requires Python 3.11 or newer. FFmpeg is required for media
operations but not for every unit test.

```bash
git clone https://github.com/ArtCog/chatmonteur.git
cd chatmonteur
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[whisper,emoji,dev]"
python -m pip install auto-editor
git config core.hooksPath .githooks
python -m pytest -q
```

The full setup scripts install the local editing toolchain used by the product,
but contributors still need the `dev` extra for the test suite:

```bash
./setup.sh
# Windows: ./setup.ps1
```

The media smoke tests require ffmpeg on `PATH`:

```bash
python tests/smoke_ffmpeg.py
python tests/smoke_cut_edl.py
```

## Adding capabilities and flows

- **Capability (tool):** add a module in `chatmonteur/tools/` that exposes
  `TOOL`.
- **Flow (pipeline):** add a YAML definition in `pipelines/`.

See [docs/extending.md](docs/extending.md). Tools must read runtime state through
`RunContext`, write only under `ctx.paths.*`, and raise on failure rather than
silently continuing.

Respect the non-negotiable production rules in
[skills/production-rules.md](skills/production-rules.md): normalize VFR input,
never stream-copy edited cuts, apply loudness normalization at the final stage,
verify audio by level, and detect the available encoder. Credit any new
third-party engine in [CREDITS.md](CREDITS.md).

## Pull requests

1. Keep the change focused and explain the user-visible or maintainer-visible
   problem it solves.
2. Add or update tests for behavior changes. A bug fix should include a
   regression test whenever practical.
3. Update the relevant user or architecture documentation when a public
   command, project artifact, gate, or tool contract changes.
4. Do not commit generated renders, private project files, credentials, or media
   whose redistribution rights are unclear.
5. Confirm `python -m pytest -q` passes. The repository CI also checks supported
   Windows/Linux environments and the HyperFrames integration.

By contributing, you agree that your contribution is licensed under the
repository's [MIT license](LICENSE).
