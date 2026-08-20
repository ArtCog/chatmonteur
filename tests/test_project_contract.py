"""The per-video filesystem contract must be impossible to miss.

These tests deliberately avoid ffmpeg.  They lock the front-door behaviour
that every agent and every ``chatmonteur edit`` run relies on.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from chatmonteur.project import (
    ProjectContractError,
    REQUIRED_DIRECTORIES,
    REQUIRED_FILES,
    import_source,
    initialize_project,
)
from chatmonteur.core.tool import ToolResult
from chatmonteur.core import ChatmonteurError


def test_initialize_project_creates_the_public_montage_contract(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "2026-real-video"

    initialize_project(
        project,
        title="Real video",
        legacy_source_root=r"C:\MONTAGE\raw",
    )

    assert all((project / relative).is_dir() for relative in REQUIRED_DIRECTORIES)
    assert all((project / relative).is_file() for relative in REQUIRED_FILES)
    assert not (project / "preproduction").exists()
    assert not (project / "youtube").exists()

    plan = (project / "PLAN.md").read_text(encoding="utf-8")
    assert "Real video" in plan
    assert r"C:\MONTAGE\raw" in plan
    assert "raw/" in plan and "renders/" in plan
    assert "preproduction/" not in plan and "youtube/" not in plan


def test_initialize_project_never_overwrites_existing_work(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "2026-existing"
    initialize_project(project, title="Original")
    plan = project / "PLAN.md"
    plan.write_text("SENTINEL\n", encoding="utf-8")

    initialize_project(project, title="Replacement")

    assert plan.read_text(encoding="utf-8") == "SENTINEL\n"


def test_import_source_puts_an_immutable_copy_in_raw(tmp_path: Path) -> None:
    source = tmp_path / "incoming" / "take.mkv"
    source.parent.mkdir()
    source.write_bytes(b"original recording")
    project = tmp_path / "projects" / "2026-video"
    initialize_project(project, title="Video")

    imported = import_source(source, project)

    assert imported == project / "raw" / "take.mkv"
    assert imported.read_bytes() == b"original recording"
    source.write_bytes(b"changed outside")
    assert imported.read_bytes() == b"original recording"


def test_import_source_refuses_to_overwrite_a_different_recording(tmp_path: Path) -> None:
    source = tmp_path / "incoming" / "take.mkv"
    source.parent.mkdir()
    source.write_bytes(b"new recording")
    project = tmp_path / "projects" / "2026-video"
    initialize_project(project, title="Video")
    (project / "raw" / "take.mkv").write_bytes(b"existing recording")

    with pytest.raises(ProjectContractError, match="already exists"):
        import_source(source, project)


def test_edit_front_door_initializes_and_imports_before_pipeline(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    from chatmonteur import cli

    source = tmp_path / "incoming.mp4"
    source.write_bytes(b"recording")
    seen: dict[str, object] = {}

    def fake_run(self, ctx, pipeline, *, initial, resume):  # noqa: ANN001
        seen["project_root"] = ctx.paths.project_root
        seen["source"] = initial["source"]["video"]
        draft = ctx.paths.renders / "mechanical-draft.mp4"
        return {"render": ToolResult(artifacts={"video": str(draft)})}

    monkeypatch.setattr(cli.PipelineRunner, "run", fake_run)
    monkeypatch.setattr(cli.media, "ffprobe_json", lambda _path: {
        "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
    })
    args = Namespace(
        input=str(source),
        root=str(tmp_path),
        project="2026-front-door",
        pipeline="talking_head",
        lut=None,
        model="tiny",
        no_resume=False,
    )

    assert cli._cmd_edit(args) == 0
    project = tmp_path / "projects" / "2026-front-door"
    assert seen["project_root"] == project
    assert seen["source"] == str(project / "raw" / "incoming.mp4")
    assert all((project / relative).exists() for relative in (*REQUIRED_DIRECTORIES, *REQUIRED_FILES))
    assert "OUTPUT:" in capsys.readouterr().out


def test_edit_front_door_refuses_ambiguous_multitrack_audio(monkeypatch, tmp_path: Path) -> None:
    """The generic pipeline must not guess which OBS track carries clean speech."""
    from chatmonteur import cli

    source = tmp_path / "obs.mkv"
    source.write_bytes(b"recording")
    monkeypatch.setattr(cli.media, "ffprobe_json", lambda _path: {
        "streams": [
            {"codec_type": "video"},
            {"codec_type": "audio", "index": 1},
            {"codec_type": "audio", "index": 2},
        ],
    })
    args = Namespace(
        input=str(source), root=str(tmp_path), project="obs", pipeline="talking_head",
        lut=None, model=None, no_resume=False,
    )

    with pytest.raises(ChatmonteurError, match="2 audio streams.*Branch B"):
        cli._cmd_edit(args)

    assert not (tmp_path / "projects" / "obs").exists()


def test_run_front_door_executes_one_capability_from_json(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    from chatmonteur import cli

    params = tmp_path / "redact-run.json"
    params.write_text(
        json.dumps({"input": "clips/draft.mp4", "plan": "transcripts/redactions.json"}),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_run(self, ctx, pipeline, *, resume):  # noqa: ANN001
        step = pipeline.steps[0]
        seen["project_root"] = ctx.paths.project_root
        seen["capability"] = step.capability
        seen["params"] = step.params
        return {
            step.id: ToolResult(
                artifacts={"video": "clips/redacted.mp4"},
                meta={"redactions": 1},
            )
        }

    monkeypatch.setattr(cli.PipelineRunner, "run", fake_run)

    rc = cli.main([
        "run", "redact",
        "--project", "2026-front-door",
        "--root", str(tmp_path),
        "--params", str(params),
    ])

    assert rc == 0
    assert seen == {
        "project_root": tmp_path / "projects" / "2026-front-door",
        "capability": "redact",
        "params": {"input": "clips/draft.mp4", "plan": "transcripts/redactions.json"},
    }
    output = json.loads(capsys.readouterr().out)
    assert output["artifacts"]["video"] == "clips/redacted.mp4"
    assert output["meta"]["redactions"] == 1


@pytest.mark.parametrize("unsafe", ["../outside", "folder/video", r"folder\video", ".", ""])
def test_init_refuses_project_names_that_escape_the_projects_container(
    tmp_path: Path, capsys, unsafe: str
) -> None:
    from chatmonteur import cli

    rc = cli.main(["init", unsafe, "--root", str(tmp_path)])

    assert rc == 1
    assert "project name" in capsys.readouterr().err
    assert not (tmp_path / "outside").exists()
