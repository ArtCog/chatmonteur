"""``chatmonteur`` command-line entry point — the mechanical front door.

    chatmonteur edit raw/talk.mp4            # raw footage -> mechanical draft
    chatmonteur edit raw/talk.mp4 --lut cool_cinema --project my-vlog
    chatmonteur tools                        # list capabilities and their backends
    chatmonteur version

An agent (Claude Code / Codex) can call exactly the same command — see CLAUDE.md
/ AGENTS.md for the orchestration contract.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from . import __version__
from . import media
from .core import (
    ChatmonteurError,
    Pipeline,
    PipelineRunner,
    RunContext,
    Step,
    ToolRegistry,
    load_config,
)
from .project import import_source, initialize_project

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKAGED_PIPELINES = Path(__file__).resolve().parent / "assets" / "pipelines"
_PIPELINES = _PACKAGED_PIPELINES if _PACKAGED_PIPELINES.is_dir() else _REPO_ROOT / "pipelines"


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

    init = sub.add_parser("init", help="create a complete per-video project contract")
    init.add_argument("project", help="project name under projects/")
    init.add_argument("--title", help="human-readable video title (default: project name)")
    init.add_argument("--root", default=".", help="workspace root holding projects/ (default: cwd)")
    init.add_argument("--legacy-source-root", default="", help="optional path to existing source material")
    init.set_defaults(func=_cmd_init)

    edit = sub.add_parser("edit", help="raw footage -> mechanical draft")
    edit.add_argument("input", help="path to the raw video")
    edit.add_argument("--project", help="project name (default: input file stem)")
    edit.add_argument("--root", default=".", help="workspace root holding projects/ (default: cwd)")
    edit.add_argument("--pipeline", default="talking_head", help="pipeline name in pipelines/")
    edit.add_argument("--lut", default=None, help="colour LUT name or .cube path (default: ungraded original)")
    edit.add_argument("--model", help="override transcription model (e.g. tiny, large-v3)")
    edit.add_argument("--no-resume", action="store_true", help="ignore checkpoints, run everything")
    edit.set_defaults(func=_cmd_edit)

    run = sub.add_parser("run", help="execute one capability from a JSON parameter object")
    run.add_argument("capability", help="capability shown by `chatmonteur tools`")
    run.add_argument("--project", required=True, help="project name under projects/")
    run.add_argument("--params", required=True, help="UTF-8 JSON file containing tool parameters")
    run.add_argument("--root", default=".", help="workspace root holding projects/ (default: cwd)")
    run.add_argument("--no-resume", action="store_true", help="ignore the capability checkpoint")
    run.set_defaults(func=_cmd_run)

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

    _refuse_ambiguous_talking_head_audio(src, args.pipeline)

    config = load_config(args.root)
    if args.model:
        config = dataclasses.replace(config, transcribe=dataclasses.replace(config.transcribe, model=args.model))

    project = args.project or src.stem
    project_root = config.projects_dir / project
    initialize_project(project_root, title=project, legacy_source_root=str(src.parent))
    src = import_source(src, project_root)
    ctx = RunContext.for_project(config, project)
    ctx.log(f"project '{project}' → {ctx.paths.project_root}")

    registry = ToolRegistry().discover()
    pipeline = Pipeline.from_yaml(pipeline_file)
    initial = {"source": {"video": str(src)}, "opts": {"lut": args.lut}}

    results = PipelineRunner(registry).run(ctx, pipeline, initial=initial, resume=not args.no_resume)

    final = results["render"].artifacts["video"]
    print(f"\nOUTPUT: {final}")
    return 0


def _refuse_ambiguous_talking_head_audio(src: Path, pipeline_name: str) -> None:
    """Keep the generic silence cut from guessing among OBS audio tracks."""
    if pipeline_name != "talking_head":
        return
    streams = media.ffprobe_json(src).get("streams", [])
    count = sum(stream.get("codec_type") == "audio" for stream in streams)
    if count > 1:
        raise ChatmonteurError(
            f"source has {count} audio streams; the talking_head pipeline cannot "
            "safely guess the clean microphone track. Use the documented OBS "
            "Branch B workflow in skills/cutting.md, then continue with "
            "`chatmonteur run`."
        )


def _cmd_init(args: argparse.Namespace) -> int:
    config = load_config(args.root)
    project_root = initialize_project(
        config.projects_dir / args.project,
        title=args.title or args.project,
        legacy_source_root=args.legacy_source_root,
    )
    print(f"PROJECT_READY {project_root}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    params_path = Path(args.params).expanduser().resolve()
    if not params_path.is_file():
        raise ChatmonteurError(f"params file not found: {params_path}")
    try:
        params = json.loads(params_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChatmonteurError(f"could not read params JSON {params_path}: {exc}") from exc
    if not isinstance(params, dict):
        raise ChatmonteurError(f"params JSON must be an object: {params_path}")

    config = load_config(args.root)
    project_root = config.projects_dir / args.project
    initialize_project(project_root, title=args.project)
    ctx = RunContext.for_project(config, args.project)
    # Keep ad-hoc runs from replacing a same-named checkpoint in a full pipeline.
    step = Step(id=f"run_{args.capability}", capability=args.capability, params=params)
    pipeline = Pipeline(name=f"run-{args.capability}", steps=(step,))
    results = PipelineRunner(ToolRegistry().discover()).run(
        ctx,
        pipeline,
        resume=not args.no_resume,
    )
    result = results[step.id]
    print(json.dumps(
        {"capability": args.capability, "artifacts": result.artifacts, "meta": result.meta},
        ensure_ascii=False,
        indent=2,
    ))
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
