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


def test_default_brand_sound_profile_references_ledgered_assets() -> None:
    """A recurring channel bed must be reusable without searching or path guessing."""
    profile = json.loads(
        (ROOT / "assets" / "brand" / "default" / "sound.json").read_text(encoding="utf-8")
    )
    ledger_ids = {
        json.loads(line)["id"]
        for line in (ROOT / "assets" / "sound" / "ledger.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }

    assert profile["selection_policy"]["default_mode"] == "default_background"
    assert profile["selection_policy"]["choices"] == [
        "default_background", "custom_sections", "no_music"
    ]
    assert profile["defaults"]["background"]["ledger_id"] in ledger_ids
    assert profile["defaults"]["ui_sfx"]["ledger_id"] in ledger_ids
def test_wheel_packages_the_runtime_brand_assets():
    """A wheel without frame.md/components works in-repo and fails after install."""
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["hooks"]["custom"]["path"] == "hatch_build.py"
    assert (root / "hatch_build.py").is_file()
    assert (root / "assets" / "brand" / "default" / "frame.md").is_file()
    assert (root / "assets" / "brand" / "default" / "catalog.json").is_file()


def test_runtime_resources_resolve_in_a_source_checkout():
    from chatmonteur.cli import _PIPELINES
    from chatmonteur.tools.color import _LUT_DIR

    assert (_PIPELINES / "talking_head.yaml").is_file()
    assert (_LUT_DIR / "cool_cinema.cube").is_file()


def test_ci_covers_tests_types_build_and_hyperframes():
    from pathlib import Path

    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "pytest tests" in workflow
    assert "pyright chatmonteur" in workflow
    assert "python -m build" in workflow
    assert "hyperframes@0.7.109 check" in workflow


def test_public_clone_has_its_own_type_check_policy():
    """CI must not inherit the maintainer workspace's parent Pyright config."""
    config = json.loads((ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))

    assert config["typeCheckingMode"] == "standard"
    assert config["reportMissingImports"] == "warning"
    assert config["reportMissingModuleSource"] == "none"
