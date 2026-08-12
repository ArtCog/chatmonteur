from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".githooks"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=check,
    )


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Hook Test")
    _git(repo, "config", "user.email", "hook@example.invalid")
    _git(repo, "config", "core.hooksPath", str(HOOKS))
    (repo / ".gitignore").write_text(
        ".env\n*.local.md\nSTATE.md\n_audit/\nчерновик/\nbank/*\n!bank/BANK.md\n",
        encoding="utf-8",
    )
    (repo / "safe.txt").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "safe.txt")
    _git(repo, "commit", "-qm", "baseline")
    return repo, _git(repo, "rev-parse", "HEAD").stdout.strip()


def _commit(repo: Path, path: str, content: str, *, force: bool = False) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", "-f" if force else "--", path)
    _git(repo, "commit", "-qm", f"add {path}")
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _run_hook(repo: Path, local_sha: str, remote_sha: str) -> subprocess.CompletedProcess[str]:
    refs = f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"
    stdin_file = repo / ".git" / "pre-push-stdin"
    stdin_file.write_bytes(refs.encode("utf-8"))
    return subprocess.run(
        [
            "git",
            "hook",
            "run",
            f"--to-stdin={stdin_file}",
            "pre-push",
            "--",
            "origin",
            "https://example.invalid/repo.git",
        ],
        cwd=repo,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_pre_push_hook_allows_safe_commits(tmp_path: Path):
    repo, remote_sha = _repo(tmp_path)
    local_sha = _commit(repo, "notes.txt", "public notes\n")

    result = _run_hook(repo, local_sha, remote_sha)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "blocked"),
    [
        (".env", True),
        ("ROADMAP.local.md", True),
        ("STATE.md", True),
        ("_audit/findings.md", True),
        ("черновик/demo.png", True),
        ("bank/gameplay/clip.mp4", True),
        (".env.example", False),
        ("bank/BANK.md", False),
    ],
)
def test_pre_push_hook_internal_path_policy(tmp_path: Path, path: str, blocked: bool):
    repo, remote_sha = _repo(tmp_path)
    local_sha = _commit(repo, path, "not secret\n", force=True)

    result = _run_hook(repo, local_sha, remote_sha)

    assert (result.returncode != 0) is blocked, result.stderr
    if blocked:
        assert path in result.stderr


@pytest.mark.parametrize(
    ("content", "blocked"),
    [
        ("PEXELS_API_" + "KEY=" + "Px1234567890abcdefghijklmnop\n", True),
        ("github_" + 'token = "' + "ghp_1234567890abcdefghijklmnop\"\n", True),
        ("PEXELS_API_KEY=replace_with_your_key_here\n", False),
        ('token = ctx.config.get_secret("FREESOUND_API_KEY")\n', False),
    ],
)
def test_pre_push_hook_secret_policy(tmp_path: Path, content: str, blocked: bool):
    repo, remote_sha = _repo(tmp_path)
    local_sha = _commit(repo, "settings.txt", content)

    result = _run_hook(repo, local_sha, remote_sha)

    assert (result.returncode != 0) is blocked, result.stderr
    if blocked:
        assert "possible secret" in result.stderr.lower()
