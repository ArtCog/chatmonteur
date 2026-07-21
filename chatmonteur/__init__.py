"""chatmonteur — agent-orchestrated talking-head video editing.

One command turns raw footage into a finished video. The core is small and
engine-agnostic: tools declare *capabilities*, pipelines order capabilities,
and the runner executes them with resumable checkpoints.
"""

__version__ = "0.1.0.dev0"
