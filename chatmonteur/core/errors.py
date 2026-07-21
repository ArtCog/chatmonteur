"""Typed errors. Tools and the runner raise these so failures are explicit
and never swallowed — a core correctness rule (no silent failures)."""

from __future__ import annotations


class ChatmonteurError(Exception):
    """Base class for all chatmonteur errors."""


class ConfigError(ChatmonteurError):
    """Invalid or missing configuration."""


class ToolError(ChatmonteurError):
    """A tool failed while running."""


class MissingDependencyError(ToolError):
    """A required binary or Python package for a tool is not installed.

    Carries the missing items and an install hint so the agent/CLI can tell
    the user exactly what to do instead of crashing opaquely.
    """

    def __init__(self, tool: str, missing: list[str], hint: str | None = None) -> None:
        self.tool = tool
        self.missing = missing
        self.hint = hint
        detail = ", ".join(missing)
        msg = f"tool '{tool}' is missing: {detail}"
        if hint:
            msg += f"\n  → {hint}"
        super().__init__(msg)


class PipelineError(ChatmonteurError):
    """A pipeline could not complete. Resume is possible from the checkpoint."""

    def __init__(self, step_id: str, cause: BaseException) -> None:
        self.step_id = step_id
        self.cause = cause
        super().__init__(f"pipeline failed at step '{step_id}': {cause}")
