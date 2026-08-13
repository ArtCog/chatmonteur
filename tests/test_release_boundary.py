"""The public repository must honor ADR-0012's montage-only release boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_tree_does_not_track_private_editorial_package() -> None:
    tracked = set(subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines())

    forbidden_prefixes = (
        ".agents/skills/youtube-editorial/",
        "docs/superpowers/plans/2026-08-02-youtube-editorial-integration.md",
        "docs/superpowers/specs/2026-08-02-editorial-lifecycle-integration-design.md",
    )
    leaked = sorted(
        path for path in tracked
        if any(path == prefix or path.startswith(prefix) for prefix in forbidden_prefixes)
    )

    assert not leaked, f"private editorial files tracked by the public repo: {leaked}"


def test_public_agent_docs_do_not_require_ignored_local_state() -> None:
    """A fresh clone must have a usable entry point without maintainer-only files."""
    docs = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("AGENTS.md", "CLAUDE.md")
    )

    assert "`STATE.md` — read it FIRST" not in docs
    assert "living state is `PLAN.local.md`" not in docs


def test_shipped_sound_pack_has_cc0_ledger_for_every_audio_file() -> None:
    sound_root = ROOT / "assets" / "sound"
    ledger_path = sound_root / "ledger.jsonl"
    entries = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_file = {entry["file"]: entry for entry in entries}
    audio_files = {
        path.relative_to(sound_root).as_posix()
        for path in sound_root.rglob("*")
        if path.suffix.lower() in {".mp3", ".ogg", ".wav", ".flac"}
    }

    assert len(audio_files) >= 2
    assert set(by_file) == audio_files
    for relative, entry in by_file.items():
        payload = (sound_root / relative).read_bytes()
        assert entry["license"] == "CC0-1.0"
        assert entry["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"
        assert entry["source_url"].startswith("https://opengameart.org/content/")
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
