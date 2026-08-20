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
    assert "hyperframes@0.8.4 check" in workflow


def test_public_clone_has_its_own_type_check_policy():
    """CI must not inherit the maintainer workspace's parent Pyright config."""
    config = json.loads((ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))

    assert config["typeCheckingMode"] == "standard"
    assert config["reportMissingImports"] == "warning"
    assert config["reportMissingModuleSource"] == "none"


def test_setup_scripts_run_from_the_repository_and_stop_on_failed_installs():
    """Quick Start must not silently install from the caller's working directory."""
    powershell = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    shell = (ROOT / "setup.sh").read_text(encoding="utf-8")

    assert "Push-Location -LiteralPath $PSScriptRoot" in powershell
    assert "Pop-Location" in powershell
    assert powershell.count("if ($LASTEXITCODE -ne 0) { throw") >= 2
    assert 'cd -- "$(dirname -- "${BASH_SOURCE[0]}")"' in shell


def test_quick_start_only_references_files_that_ship():
    readmes = [
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "README.ru.md")
    ]

    assert all("--params examples/sound-run.json" in readme for readme in readmes)
    assert (ROOT / "examples" / "sound-run.json").is_file()


def test_agent_guides_route_motion_selection_through_the_active_brand():
    guides = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("AGENTS.md", "CLAUDE.md", "skills/motion.md")
    )

    assert "assets/brand/<name>/SELECTION-GUIDE.md" in guides
    assert "active brand" in guides
    assert "assets/brand/default/SELECTION-GUIDE.md" not in guides


def test_release_copy_does_not_advertise_unshipped_runtime_backends():
    readmes = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "README.ru.md")
    )
    credits = (ROOT / "CREDITS.md").read_text(encoding="utf-8")
    example_config = (ROOT / "config.example.toml").read_text(encoding="utf-8")

    assert "ElevenLabs" not in readmes
    assert 'backend = "faster-whisper"' not in example_config
    assert "video-use methodology" in readmes
    assert "video-use** | editorial methodology" in credits


def test_public_pipeline_docs_keep_color_below_captions_and_loudness_last():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    pipeline = (ROOT / "pipelines" / "talking_head.yaml").read_text(encoding="utf-8")
    readmes = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("README.md", "README.ru.md")
    )

    assert "transcribe → color → subtitles → render" in agents
    assert "normalize (CFR + linear level prep)" in pipeline
    assert "burn subtitles -> color" not in pipeline
    assert "loudnorm" not in pipeline.split("steps:", 1)[0]
    assert "normalize (clean CFR, −14 LUFS)" not in readmes
    assert "нормализация (CFR, −14 LUFS)" not in readmes


def test_release_version_is_consistent():
    import tomllib

    from chatmonteur import __version__

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == "0.1.0"
    assert __version__ == "0.1.0"


def test_setup_generated_local_config_is_ignored():
    result = subprocess.run(
        ["git", "check-ignore", "config.toml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "config.toml"


def test_local_build_artifacts_are_ignored():
    result = subprocess.run(
        ["git", "check-ignore", "dist/chatmonteur-0.1.0.tar.gz"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_public_tree_has_no_maintainer_home_paths():
    maintainer_home = "C:/Users/" + "magme"
    result = subprocess.run(
        ["git", "grep", "-n", maintainer_home],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stdout
