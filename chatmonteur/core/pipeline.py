"""Pipeline definition + runner.

A pipeline is an ordered list of steps. Each step asks for a *capability*; the
runner picks an available tool that provides it (honouring a backend preference),
runs it, and checkpoints the result. Params may reference upstream artifacts with
``${step_id.artifact}`` so steps chain without hardcoding paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .checkpoint import Checkpoint
from .context import RunContext
from .errors import ConfigError, PipelineError, ToolError
from .tool import Tool, ToolRegistry, ToolResult

_REF = re.compile(r"\$\{([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}")


@dataclass(frozen=True)
class Step:
    id: str
    capability: str
    params: dict[str, Any] = field(default_factory=dict)
    backend: str | None = None  # prefer a tool whose manifest lists this backend
    when: str | None = None  # option flag; step runs only if options[when] is truthy


@dataclass(frozen=True)
class Pipeline:
    name: str
    steps: tuple[Step, ...]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Pipeline":
        path = Path(path)
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError) as exc:
            raise ConfigError(f"could not read pipeline {path}: {exc}") from exc

        name = data.get("name") or path.stem
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ConfigError(f"pipeline {path}: 'steps' must be a non-empty list")

        steps: list[Step] = []
        seen: set[str] = set()
        for i, raw in enumerate(raw_steps):
            if not isinstance(raw, dict) or "capability" not in raw:
                raise ConfigError(f"pipeline {path}: step #{i} needs a 'capability'")
            step_id = raw.get("id") or raw["capability"]
            if step_id in seen:
                raise ConfigError(f"pipeline {path}: duplicate step id '{step_id}'")
            seen.add(step_id)
            steps.append(
                Step(
                    id=step_id,
                    capability=raw["capability"],
                    params=raw.get("params", {}) or {},
                    backend=raw.get("backend"),
                    when=raw.get("when"),
                )
            )
        return cls(name=name, steps=tuple(steps))


class PipelineRunner:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def run(
        self,
        ctx: RunContext,
        pipeline: Pipeline,
        *,
        options: dict[str, Any] | None = None,
        initial: dict[str, dict[str, str]] | None = None,
        resume: bool = True,
    ) -> dict[str, ToolResult]:
        """Execute the pipeline, returning each step's result by step id.

        ``initial`` seeds pseudo-steps (e.g. ``source``, ``opts``) so the CLI can
        inject the input path / chosen LUT via ``${source.video}`` references.
        """
        options = options or {}
        checkpoint = Checkpoint.for_project(ctx.paths.project_root)
        results: dict[str, ToolResult] = {
            sid: ToolResult(artifacts=dict(arts)) for sid, arts in (initial or {}).items()
        }

        for step in pipeline.steps:
            if step.when and not options.get(step.when):
                ctx.log(f"skip '{step.id}' (option '{step.when}' off)")
                continue

            artifacts_so_far = {sid: r.artifacts for sid, r in results.items()}
            params = _resolve(step.params, artifacts_so_far)
            input_hash = Checkpoint.hash_inputs({"params": params, "cap": step.capability})

            if resume and checkpoint.is_done(step.id, input_hash):
                ctx.log(f"✓ '{step.id}' cached")
                results[step.id] = ToolResult(artifacts=checkpoint.artifacts(step.id))
                continue

            tool = self._pick_tool(step)
            ctx.log(f"▶ '{step.id}' via {tool.manifest.name}")
            try:
                result = tool.run(ctx, **params)
            except ToolError:
                raise
            except Exception as exc:  # noqa: BLE001 - wrap anything as a resumable failure
                raise PipelineError(step.id, exc) from exc

            checkpoint.record(step.id, input_hash, result.artifacts, result.meta)
            results[step.id] = result

        return results

    def _pick_tool(self, step: Step) -> Tool:
        candidates = self.registry.for_capability(step.capability)
        if not candidates:
            raise PipelineError(step.id, ToolError(f"no tool provides capability '{step.capability}'"))

        # Honour an explicit backend preference, if any tool advertises it.
        if step.backend:
            preferred = [t for t in candidates if step.backend in t.manifest.backends]
            candidates = preferred or candidates

        # Prefer a tool whose requirements are already satisfied (free, installed).
        ready = [t for t in candidates if not t.missing_requirements()]
        chosen = (ready or candidates)[0]
        return chosen


def _resolve(params: Any, artifacts: dict[str, dict[str, str]]) -> Any:
    """Substitute ``${step.artifact}`` references inside string params."""
    if isinstance(params, str):
        def sub(m: "re.Match[str]") -> str:
            step_id, key = m.group(1), m.group(2)
            try:
                return artifacts[step_id][key]
            except KeyError:
                raise ConfigError(f"unknown reference ${{{step_id}.{key}}}") from None
        return _REF.sub(sub, params)
    if isinstance(params, dict):
        return {k: _resolve(v, artifacts) for k, v in params.items()}
    if isinstance(params, list):
        return [_resolve(v, artifacts) for v in params]
    return params
