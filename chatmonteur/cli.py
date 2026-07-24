"""``chatmonteur`` command-line entry point — the "one command" front door.

    chatmonteur edit raw/talk.mp4            # raw footage -> finished video
    chatmonteur edit raw/talk.mp4 --lut cool_cinema --project my-vlog
    chatmonteur tools                        # list capabilities and their backends
    chatmonteur version

An agent (Claude Code / Codex) can call exactly the same command — see CLAUDE.md
/ AGENTS.md for the orchestration contract.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from . import __version__
from .core import (
    ChatmonteurError,
    Pipeline,
    PipelineRunner,
    RunContext,
    ToolRegistry,
    load_config,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIPELINES = _REPO_ROOT / "pipelines"


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to a legacy codepage; force UTF-8 so logs/paths
    # with non-ASCII never crash the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ChatmonteurError as exc:
        print(f"chatmonteur: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nchatmonteur: interrupted (resume with the same command)", file=sys.stderr)
        return 130


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="chatmonteur", description="Agent-orchestrated talking-head video editing.")
    sub = p.add_subparsers(dest="command", required=True)

    edit = sub.add_parser("edit", help="raw footage -> finished video")
    edit.add_argument("input", help="path to the raw video")
    edit.add_argument("--project", help="project name (default: input file stem)")
    edit.add_argument("--root", default=".", help="workspace root holding projects/ (default: cwd)")
    edit.add_argument("--pipeline", default="talking_head", help="pipeline name in pipelines/")
    edit.add_argument("--lut", default=None, help="colour LUT name or .cube path (default: ungraded original)")
    edit.add_argument("--model", help="override transcription model (e.g. tiny, large-v3)")
    edit.add_argument("--no-resume", action="store_true", help="ignore checkpoints, run everything")
    edit.set_defaults(func=_cmd_edit)

    tools = sub.add_parser("tools", help="list capabilities and tools")
    tools.set_defaults(func=_cmd_tools)

    ver = sub.add_parser("version", help="print version")
    ver.set_defaults(func=lambda _a: (print(f"chatmonteur {__version__}"), 0)[1])

    return p


def _cmd_edit(args: argparse.Namespace) -> int:
    src = Path(args.input).expanduser().resolve()
    if not src.is_file():
        print(f"chatmonteur: input not found: {src}", file=sys.stderr)
        return 1

    pipeline_file = _PIPELINES / f"{args.pipeline}.yaml"
    if not pipeline_file.is_file():
        available = ", ".join(sorted(f.stem for f in _PIPELINES.glob("*.yaml"))) or "(none)"
        print(f"chatmonteur: pipeline '{args.pipeline}' not found. Available: {available}", file=sys.stderr)
        return 1

    config = load_config(args.root)
    if args.model:
        config = dataclasses.replace(config, transcribe=dataclasses.replace(config.transcribe, model=args.model))

    project = args.project or src.stem
    ctx = RunContext.for_project(config, project)
    ctx.log(f"project '{project}' → {ctx.paths.project_root}")

    registry = ToolRegistry().discover()
    pipeline = Pipeline.from_yaml(pipeline_file)
    initial = {"source": {"video": str(src)}, "opts": {"lut": args.lut}}

    results = PipelineRunner(registry).run(ctx, pipeline, initial=initial, resume=not args.no_resume)

    final = results["render"].artifacts["video"]
    print(f"\nDONE: {final}")
    return 0


def _cmd_tools(_args: argparse.Namespace) -> int:
    registry = ToolRegistry().discover()
    print("chatmonteur capabilities:\n")
    for cap in sorted(registry._by_capability):  # noqa: SLF001 - simple introspection
        for tool in registry.for_capability(cap):
            missing = tool.missing_requirements()
            status = "ready" if not missing else f"missing: {', '.join(missing)}"
            tag = "" if tool.manifest.cost == "free" else f" [{tool.manifest.cost}]"
            print(f"  {cap:<12} {tool.manifest.name}{tag}  ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
