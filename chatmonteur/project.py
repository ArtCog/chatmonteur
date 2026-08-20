"""Canonical per-video project initialization and source import.

The filesystem is the hand-off between editorial agents, montage agents and
future sessions.  Creating only the folders needed by the current command is
therefore not enough: every front door creates the complete production
contract, idempotently, before doing media work.
"""

from __future__ import annotations

import filecmp
import re
import shutil
from pathlib import Path

from .core.errors import ChatmonteurError


class ProjectContractError(ChatmonteurError):
    """The project cannot be initialized or imported without losing work."""


REQUIRED_DIRECTORIES = (
    "raw",
    "assets",
    "clips",
    "transcripts",
    "compositions",
    "previews",
    "renders",
)

REQUIRED_FILES = (
    "PLAN.md",
)

_TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates" / "project"
_PROJECT_NAME = re.compile(r"^[^\W][\w.-]*$", re.UNICODE)


def resolve_project_root(projects_dir: str | Path, name: str) -> Path:
    """Resolve one safe project slug below ``projects_dir``.

    Project names are identifiers, not paths.  Rejecting separators and dot
    segments keeps every public CLI front door inside the mandatory
    ``projects/<name>/`` container on Windows, macOS, and Linux.
    """
    if not name or name in {".", ".."} or not _PROJECT_NAME.fullmatch(name):
        raise ProjectContractError(
            "project name must be one slug using letters, numbers, '.', '_' or '-'"
        )
    return Path(projects_dir).resolve() / name


def initialize_project(
    project_root: str | Path,
    *,
    title: str,
    legacy_source_root: str = "",
) -> Path:
    """Create the complete per-video contract without overwriting any file."""
    root = Path(project_root).resolve()
    for relative in REQUIRED_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)

    for relative in REQUIRED_FILES:
        source = _TEMPLATE_ROOT / relative
        if not source.is_file():
            raise ProjectContractError(f"project template is missing: {source}")
        destination = root / relative
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_text(encoding="utf-8")
        content = content.replace("{{PROJECT_TITLE}}", title)
        content = content.replace("{{LEGACY_SOURCE_ROOT}}", legacy_source_root)
        destination.write_text(content, encoding="utf-8")

    return root


def import_source(source: str | Path, project_root: str | Path) -> Path:
    """Put an immutable working copy of a recording in ``raw/``.

    Existing identical media is reused.  A same-name, different file is never
    overwritten because that would silently replace the source of record.
    """
    src = Path(source).resolve()
    if not src.is_file():
        raise ProjectContractError(f"source recording not found: {src}")

    raw = Path(project_root).resolve() / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    destination = raw / src.name

    if src == destination.resolve():
        return destination
    if destination.exists():
        if filecmp.cmp(src, destination, shallow=False):
            return destination
        raise ProjectContractError(
            f"raw source already exists with different content: {destination}"
        )

    shutil.copy2(src, destination)
    return destination
