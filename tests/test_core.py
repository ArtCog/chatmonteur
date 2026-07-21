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
from chatmonteur.tools.cut_meaning import _invert, _merge, _removed_intervals  # noqa: E402


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


def test_cut_removes_filler_and_pause():
    # words: hello | um(filler) | world | <gap> | bye
    words = [
        {"start": 0.0, "end": 0.5, "word": "hello"},
        {"start": 0.5, "end": 1.0, "word": "um"},
        {"start": 1.0, "end": 1.5, "word": "world"},
        {"start": 2.5, "end": 3.0, "word": "bye"},
    ]
    removed = _removed_intervals(words, {"um"}, pause_max=0.7, keep_pad=0.12)
    keep = _invert(removed, duration=3.0, min_len=0.1)
    # 'um' [0.5,1.0] removed; pause [1.62,2.38] removed → 3 kept ranges
    assert len(keep) == 3
    kept = sum(b - a for a, b in keep)
    assert 1.5 < kept < 2.2  # shortened, but not gutted


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
    expected = {"normalize", "transcribe", "cut_silence", "cut_meaning", "subtitles", "color", "motion", "render"}
    assert expected <= caps
