"""Tool contract + registry.

A *tool* implements a single *capability* (e.g. ``transcribe``, ``cut_silence``)
by wrapping a best-of-breed engine. Pipelines reference capabilities, not tools,
so the engine underneath is swappable.

A tool module under ``chatmonteur.tools`` exposes a module-level ``TOOL`` instance::

    TOOL = MyTool()

The registry discovers it automatically.
"""

from __future__ import annotations

import importlib
import pkgutil
import shutil
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .context import RunContext
from .errors import MissingDependencyError


@dataclass(frozen=True)
class ToolManifest:
    name: str  # unique, e.g. "transcribe_whisper"
    capability: str  # what it provides, e.g. "transcribe"
    summary: str
    version: str = "0.1.0"
    backends: tuple[str, ...] = ()  # engines this tool can drive
    requires_bin: tuple[str, ...] = ()  # CLI binaries that must be on PATH
    requires_py: tuple[str, ...] = ()  # importable modules that must exist
    cost: str = "free"  # "free" | "paid" (calls a paid API)


@dataclass
class ToolResult:
    """Outputs of a tool run. ``artifacts`` maps a logical name to a file path
    (e.g. ``{"transcript": ".../master.json"}``) so later steps can consume them."""

    artifacts: dict[str, str] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


class Tool(ABC):
    manifest: ToolManifest

    @abstractmethod
    def run(self, ctx: RunContext, **params) -> ToolResult:
        """Do the work. Raise a ToolError subclass on failure — never return
        a partial result silently."""

    def missing_requirements(self) -> list[str]:
        """Return the binaries/modules this tool needs but that aren't present."""
        missing: list[str] = []
        for binary in self.manifest.requires_bin:
            if shutil.which(binary) is None:
                missing.append(f"binary:{binary}")
        for module in self.manifest.requires_py:
            if importlib.util.find_spec(module) is None:
                missing.append(f"python:{module}")
        return missing

    def ensure_ready(self, hint: str | None = None) -> None:
        missing = self.missing_requirements()
        if missing:
            raise MissingDependencyError(self.manifest.name, missing, hint)


class ToolRegistry:
    """Holds tools, indexed by name and by capability."""

    def __init__(self) -> None:
        self._by_name: dict[str, Tool] = {}
        self._by_capability: dict[str, list[Tool]] = {}

    def register(self, tool: Tool) -> None:
        name = tool.manifest.name
        if name in self._by_name:
            raise ValueError(f"duplicate tool name: {name}")
        self._by_name[name] = tool
        self._by_capability.setdefault(tool.manifest.capability, []).append(tool)

    def get(self, name: str) -> Tool:
        return self._by_name[name]

    def for_capability(self, capability: str) -> list[Tool]:
        return list(self._by_capability.get(capability, []))

    def discover(self, package: str = "chatmonteur.tools") -> "ToolRegistry":
        """Import every submodule of ``package`` and register its ``TOOL``.

        Tools that fail to import (e.g. an optional dep missing at import time)
        are skipped — their absence surfaces later as a clear MissingDependency
        when something actually needs that capability.
        """
        try:
            pkg = importlib.import_module(package)
        except ModuleNotFoundError:
            return self
        for info in pkgutil.iter_modules(pkg.__path__):
            try:
                module = importlib.import_module(f"{package}.{info.name}")
            except Exception as exc:  # noqa: BLE001 - optional deps may be absent
                # Skipping is right for a missing optional dep — but silently
                # hiding a SyntaxError turns a broken tool into a tool that
                # "doesn't exist". Say what was skipped and why.
                print(f"[chatmonteur] tool '{info.name}' not loaded: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                continue
            tool = getattr(module, "TOOL", None)
            if isinstance(tool, Tool):
                self.register(tool)
        return self
