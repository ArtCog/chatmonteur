"""Run context: the per-project paths + config + logger handed to every tool.

A tool never hardcodes ``C:\\MONTAGE\\...``; it reads everything it needs from
the RunContext, which is how the project stays portable across machines.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import Config


@dataclass(frozen=True)
class ProjectPaths:
    """Canonical per-project layout (mirrors the proven studio convention).

    Golden rule: never write to ``raw/`` or the repo root; finals go only to
    ``renders/``.
    """

    project_root: Path  # projects/<name>

    @property
    def clips(self) -> Path:
        return self.project_root / "clips"

    @property
    def transcripts(self) -> Path:
        return self.project_root / "transcripts"

    @property
    def assets(self) -> Path:
        return self.project_root / "assets"

    @property
    def compositions(self) -> Path:
        return self.project_root / "compositions"

    @property
    def previews(self) -> Path:
        return self.project_root / "previews"

    @property
    def renders(self) -> Path:
        return self.project_root / "renders"

    def ensure(self) -> "ProjectPaths":
        """Create every subdirectory. Idempotent."""
        for p in (
            self.clips,
            self.transcripts,
            self.assets,
            self.compositions,
            self.previews,
            self.renders,
        ):
            p.mkdir(parents=True, exist_ok=True)
        return self


def _default_logger(msg: str) -> None:
    print(f"[chatmonteur] {msg}", file=sys.stderr)


@dataclass
class RunContext:
    config: Config
    project: str
    paths: ProjectPaths
    log: Callable[[str], None] = _default_logger

    @classmethod
    def for_project(cls, config: Config, project: str, log: Callable[[str], None] | None = None) -> "RunContext":
        paths = ProjectPaths(config.projects_dir / project).ensure()
        return cls(config=config, project=project, paths=paths, log=log or _default_logger)
