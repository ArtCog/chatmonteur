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
from chatmonteur.tools.subtitles import (  # noqa: E402
    _break_lines, _build_cues, _fit_timing, _is_orphan, _to_ass,
)


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


# --- subtitle variants (pure ASS generation, no ffmpeg) ------------------------

_SUBS = {
    "segments": [{
        "start": 0.0, "end": 2.4, "text": "Claude Code это агент",
        "words": [
            {"start": 0.0, "end": 0.5, "word": "Claude"},
            {"start": 0.5, "end": 1.0, "word": " Code"},
            {"start": 1.0, "end": 1.4, "word": " это"},
            {"start": 1.4, "end": 2.4, "word": " агент", "emph": True},
        ],
    }],
}


def test_cue_keeps_its_words():
    cues = _build_cues(_SUBS, 42)
    assert len(cues) == 1 and len(cues[0]["words"]) == 4  # words survive for A/B/D


def _ass(variant, font="Golos Text"):
    return _to_ass(_SUBS, 42, 1920, 1080, font, variant)


def test_variant_clean_has_no_per_word_motion():
    assert "\\t(" not in _ass("clean")  # C is a static line


def test_variant_read_aloud_fades_each_word():
    ass = _ass("read_aloud")
    assert ass.count("\\t(") == 4 and "\\alpha&HFF&" in ass  # 4 words, each fades in


def test_variant_accent_colors_only_the_emph_word():
    green = _ass("accent")  # brand green by default, exactly one word marked
    assert green.count("\\1c&H6AE82B&") == 1
    yellow = _to_ass(_SUBS, 42, 1920, 1080, "Golos Text", "accent", "yellow")
    assert yellow.count("\\1c&H00D7FF&") == 1


def test_variant_typewriter_is_mono_with_cursor():
    ass = _ass("typewriter", font="JetBrains Mono")
    assert "JetBrains Mono" in ass and "▌" in ass and "\\t(" in ass


def test_no_plate_no_outline_shadow_only():
    for variant in ("clean", "accent", "highlight", "read_aloud", "typewriter"):
        ass = _ass(variant)
        assert "Style: Plate," not in ass, variant
        style = next(l for l in ass.splitlines() if l.startswith("Style: Default"))
        parts = style.split(",")
        border_style, outline, shadow = parts[15], parts[16], parts[17]
        assert border_style == "1" and outline == "0" and int(shadow) >= 2, variant


def test_variant_highlight_colors_each_word_in_turn():
    ass = _ass("highlight")
    assert ass.count("\\1c&H6AE82B&") == 4  # every word takes the accent at its time
    assert ass.count("\\1c&HF7FAFA&") == 4  # and flips back to paper after


def test_fit_timing_extends_a_flashing_cue():
    cues = [{"start": 0.0, "end": 0.2, "text": "Да", "words": []}]
    _fit_timing(cues)
    assert cues[0]["end"] >= 0.83  # never flash below min duration


def test_fit_timing_extends_fast_cue_for_cps():
    # 34 chars in 0.5 s = 68 CPS → must extend toward ≤17 CPS (2.0 s)
    cues = [{"start": 0.0, "end": 0.5, "text": "тридцать четыре символа ровно текст", "words": []}]
    _fit_timing(cues)
    assert cues[0]["end"] >= len(cues[0]["text"]) / 17.0 - 1e-9


def test_fit_timing_never_overlaps_next():
    cues = [{"start": 0.0, "end": 0.2, "text": "первая длинная реплика", "words": []},
            {"start": 0.5, "end": 1.5, "text": "вторая", "words": []}]
    _fit_timing(cues)
    assert cues[0]["end"] <= cues[1]["start"] - 0.08 + 1e-9


def test_flash_cue_merges_into_previous_when_next_is_adjacent():
    # extension can't help (next cue starts immediately) → tail merges backward
    data = {"segments": [
        {"start": 0.0, "end": 2.0, "text": "первая длинная реплика", "words": []},
        {"start": 2.0, "end": 2.3, "text": "хвост", "words": []},
        {"start": 2.3, "end": 5.0, "text": "следующее предложение", "words": []},
    ]}
    cues = _build_cues(data, 39)
    assert len(cues) == 2 and cues[0]["text"].endswith("хвост")
    assert all(c["end"] - c["start"] >= 0.83 for c in cues)


def test_line_break_carries_preposition_down():
    words = "это очень длинная строка про агентов и код".split()
    lines = _break_lines(words, 20)
    for ln in lines[:-1]:  # no non-final line ends on a function word
        assert not _is_orphan(words[ln[-1]])


def test_geometry_is_locked_at_1080p():
    style = next(l for l in _ass("clean").splitlines() if l.startswith("Style: Default"))
    assert ",59," in style and ",192,192,97," in style  # 5.5% size, 80% width, 9% margin


def test_unknown_variant_rejected(tmp_path):
    reg = ToolRegistry().discover()
    tool = reg.get("subtitles_ffmpeg")
    tr = tmp_path / "t.json"
    tr.write_text('{"segments": []}')
    from chatmonteur.core import RunContext
    ctx = RunContext.for_project(load_config(tmp_path), "t")
    with pytest.raises(ToolError):
        tool.run(ctx, input="x.mp4", transcript=str(tr), variant="sparkle")


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
