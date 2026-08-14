"""Hatch build hook: ship runtime brand packs without local design evidence."""

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


_LOCAL_ONLY_PARTS = {"source", "snapshots", ".thumbnails", "__pycache__"}


class CustomBuildHook(BuildHookInterface):
    """Map authoring-time brand assets into the installed Python package."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if self.target_name != "wheel":
            return
        force_include: dict[str, str] = build_data["force_include"]
        self._include_tree(
            Path(self.root) / "assets" / "brand",
            Path("chatmonteur") / "assets" / "brand",
            force_include,
            skip_local=True,
        )
        self._include_tree(
            Path(self.root) / "pipelines",
            Path("chatmonteur") / "assets" / "pipelines",
            force_include,
        )
        self._include_tree(
            Path(self.root) / "presets",
            Path("chatmonteur") / "assets" / "presets",
            force_include,
        )

    @staticmethod
    def _include_tree(
        source: Path,
        target_root: Path,
        force_include: dict[str, str],
        *,
        skip_local: bool = False,
    ) -> None:
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            excluded = skip_local and bool(_LOCAL_ONLY_PARTS & set(relative.parts))
            if path.is_file() and not excluded:
                target = target_root / relative
                force_include[str(path)] = target.as_posix()
