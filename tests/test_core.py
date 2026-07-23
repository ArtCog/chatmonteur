"""Fast guard tests (no ffmpeg). Run: pytest tests/test_core.py

These lock the contracts that make 'one command' safe: cut math, config
defaults, pipeline parsing, registry discovery, param resolution.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatmonteur.core import Pipeline, ToolRegistry, load_config  # noqa: E402
from chatmonteur.core.config import Config  # noqa: E402
from chatmonteur.core.errors import ConfigError  # noqa: E402
from chatmonteur.core.errors import ToolError  # noqa: E402
from chatmonteur.tools.cut_edl import _invert, _keep_ranges, _merge  # noqa: E402


def test_defaults_are_free_and_cross_platform(tmp_path):
    cfg = load_config(tmp_path)
    assert isinstance(cfg, Config)
    assert cfg.transcribe.backend == "faster-whisper"  # free, local
    assert cfg.encode.encoder == "auto"  # never hardcoded NVENC
    assert cfg.encode.loudness_lufs == -14.0


def test_config_unknown_keys_ignored(tmp_path):
    (tmp_path / "config.toml").write_text('[encode]\nfinal_height = 1080\nbogus = 5\n')
    cfg = load_config(tmp_path)
    assert cfg.encode.final_height == 1080  # known applied, unknown ignored


def test_merge_overlapping():
    assert _merge([[0, 1], [0.5, 2], [3, 4]]) == [[0, 2], [3, 4]]


def test_edl_removed_inverts_to_keep():
    # agent removed [1.0, 2.0] from a 3s clip → keep [0,1] + [2,3]
    keep = _keep_ranges({"removed": [[1.0, 2.0]]}, duration=3.0)
    assert keep == [[0.0, 1.0], [2.0, 3.0]]


def test_edl_keep_is_clamped_and_merged():
    # overlapping + out-of-bounds keep ranges are normalised, tiny slivers dropped
    keep = _keep_ranges({"keep": [[-1.0, 1.0], [0.5, 2.0], [2.9, 2.95], [2.5, 99.0]]}, duration=3.0)
    assert keep == [[0.0, 2.0], [2.5, 3.0]]


def test_edl_requires_keep_or_removed():
    with pytest.raises(ToolError):
        _keep_ranges({}, duration=3.0)


def test_pipeline_parse_and_duplicate_id(tmp_path):
    good = tmp_path / "p.yaml"
    good.write_text("name: t\nsteps:\n  - capability: normalize\n  - id: r\n    capability: render\n")
    pl = Pipeline.from_yaml(good)
    assert pl.name == "t" and [s.id for s in pl.steps] == ["normalize", "r"]

    dup = tmp_path / "d.yaml"
    dup.write_text("steps:\n  - {id: x, capability: a}\n  - {id: x, capability: b}\n")
    with pytest.raises(ConfigError):
        Pipeline.from_yaml(dup)


def test_registry_discovers_all_capabilities():
    reg = ToolRegistry().discover()
    caps = set(reg._by_capability)
    expected = {"normalize", "transcribe", "cut_silence", "cut_edl", "subtitles", "color", "motion", "render"}
    assert expected <= caps
