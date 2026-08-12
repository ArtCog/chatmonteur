"""The per-video filesystem contract must be impossible to miss.

These tests deliberately avoid ffmpeg.  They lock the front-door behaviour
that every agent and every ``chatmonteur edit`` run relies on.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from chatmonteur.project import (
    ProjectContractError,
    REQUIRED_DIRECTORIES,
    REQUIRED_FILES,
    import_source,
    initialize_project,
)
from chatmonteur.core.tool import ToolResult


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


def test_edit_front_door_initializes_and_imports_before_pipeline(monkeypatch, tmp_path: Path) -> None:
    from chatmonteur import cli

    source = tmp_path / "incoming.mp4"
    source.write_bytes(b"recording")
    seen: dict[str, object] = {}

    def fake_run(self, ctx, pipeline, *, initial, resume):  # noqa: ANN001
        seen["project_root"] = ctx.paths.project_root
        seen["source"] = initial["source"]["video"]
        final = ctx.paths.renders / "final.mp4"
        return {"render": ToolResult(artifacts={"video": str(final)})}

    monkeypatch.setattr(cli.PipelineRunner, "run", fake_run)
    args = SimpleNamespace(
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
