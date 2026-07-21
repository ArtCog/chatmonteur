"""chatmonteur core — config, tool registry, pipeline runner, checkpoints.

This package is the stable contract layer. It knows nothing about ffmpeg,
whisper, or any specific engine; it only knows how to load config, discover
tools by capability, and run a pipeline step-by-step with resume.
"""

from .errors import (
    ChatmonteurError,
    ConfigError,
    MissingDependencyError,
    PipelineError,
    ToolError,
)
from .config import Config, load_config
from .context import ProjectPaths, RunContext
from .tool import Tool, ToolManifest, ToolRegistry, ToolResult
from .checkpoint import Checkpoint
from .pipeline import Pipeline, PipelineRunner, Step

__all__ = [
    "ChatmonteurError",
    "ConfigError",
    "ToolError",
    "MissingDependencyError",
    "PipelineError",
    "Config",
    "load_config",
    "ProjectPaths",
    "RunContext",
    "Tool",
    "ToolManifest",
    "ToolResult",
    "ToolRegistry",
    "Checkpoint",
    "Pipeline",
    "Step",
    "PipelineRunner",
]
