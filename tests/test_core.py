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
import json  # noqa: E402
import re as _re  # noqa: E402

from chatmonteur.tools.inserts import _emoji_bottom as _ins_emoji_bottom  # noqa: E402
from chatmonteur.tools.zooms import _centre_expr, _zoom_expr  # noqa: E402
from chatmonteur.tools.zooms import _load_plan as _load_zoom_plan  # noqa: E402
from chatmonteur.tools.inserts import _filter_graph as _ins_filter_graph  # noqa: E402
from chatmonteur.tools.inserts import _load_plan as _load_ins_plan  # noqa: E402
from chatmonteur.tools.inserts import _to_ass as _ins_to_ass  # noqa: E402
from chatmonteur.tools.overlays import _filter_graph as _ovl_filter_graph  # noqa: E402
from chatmonteur.tools.overlays import _load_plan as _load_ovl_plan  # noqa: E402
from chatmonteur.tools.sound import _load_plan as _load_sound_plan  # noqa: E402
from chatmonteur.tools.sound import _next_input_index as _snd_next_index  # noqa: E402
from chatmonteur.tools.sound import _sfx_delay_ms  # noqa: E402
from chatmonteur.tools.stock import _match_memes  # noqa: E402
from chatmonteur.tools.stock import _providers_for as _stock_providers  # noqa: E402
from chatmonteur.tools.storyboard import _SECTIONS as _SB_SECTIONS  # noqa: E402
from chatmonteur.tools.storyboard import TOOL as _SB_TOOL  # noqa: E402
from chatmonteur.tools.storyboard import _check_one_text_at_a_time as _sb_check_text  # noqa: E402
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


# --- meaning-inserts (pure ASS generation, no ffmpeg) --------------------------

_INS = [{"start": 5.5, "end": 8.8, "emoji": "🚫",
         "text": "ноль программ монтажа", "key": "ноль программ"}]


def _ins_ass(style="emoji_top", accent="yellow", items=None):
    return _ins_to_ass(items or _INS, 1920, 1080, "Golos Text", style, accent)


def test_insert_emoji_is_overlaid_as_a_picture_not_ass():
    # libass renders outline glyphs only → a colour emoji would come out grey.
    ass = _ins_ass()
    assert "🚫" not in ass
    assert len([l for l in ass.splitlines() if l.startswith("Dialogue:")]) == 1
    graph = _ins_filter_graph("i.ass", "", [{"start": 5.5, "end": 8.8}], 1080)
    assert "overlay=(W-w)/2:H-h-" in graph and "enable='between(t,5.500,8.800)'" in graph
    assert graph.endswith("format=yuv420p[v]")


def test_insert_emoji_clears_the_text_line():
    # the emoji's bottom must sit above the text block, never on top of it
    assert _ins_emoji_bottom(1080) > round(0.11 * 1080)


def test_insert_emoji_clears_multiline_text():
    # dogfood v2: a two-line insert put the emoji ON the first line — clearance
    # must grow with the wrapped line count, per insert
    # the extra clearance must be a full extra text line, whatever the font size is
    from chatmonteur.tools.inserts import _TEXT_FRAC
    assert _ins_emoji_bottom(1080, lines=2) - _ins_emoji_bottom(1080, 1) >= _TEXT_FRAC * 1080
    graph = _ins_filter_graph("i.ass", "", [
        {"start": 1.0, "end": 3.0, "lines": 1},
        {"start": 5.0, "end": 8.0, "lines": 2},
    ], 1080)
    bottoms = [int(m) for m in _re.findall(r"H-h-(\d+)", graph)]
    assert bottoms[1] > bottoms[0]


def test_insert_colors_only_the_key_words():
    ass = _ins_ass()
    assert ass.count("\\1c&H00D7FF&") == 1  # juicy yellow, once
    assert "\\1c" not in _ins_ass(items=[{**_INS[0], "key": ""}])  # no key → plain line


def test_insert_key_missing_from_text_falls_back_to_plain():
    ass = _ins_ass(items=[{**_INS[0], "key": "которого там нет"}])
    assert "\\1c" not in ass


def test_insert_standard_has_no_plate_sticker_does():
    std = next(l for l in _ins_ass().splitlines() if l.startswith("Style: Ins"))
    assert std.split(",")[15] == "1"  # BorderStyle 1 + shadow only
    stick = next(l for l in _ins_ass("sticker").splitlines() if l.startswith("Style: Ins"))
    assert stick.split(",")[15] == "3"  # paper plate
    # on the paper plate the accent must switch to a paper-safe colour
    assert "\\1c&H0C59E8&" in _ins_ass("sticker")


def test_insert_plan_rejects_bad_ranges(tmp_path):
    plan = tmp_path / "i.json"
    plan.write_text('{"inserts": [{"start": 3, "end": 3, "text": "x"}]}', encoding="utf-8")
    with pytest.raises(ToolError):
        _load_ins_plan(plan)


# --- zooms (pure expression generation, no ffmpeg) -----------------------------

def _zoom_items(*overrides):
    base = {"start": 3.0, "end": 6.0, "kind": "punch", "scale": 1.15, "cx": 0.5, "cy": 0.40}
    return [{**base, **o} for o in (overrides or ({},))]


def test_zoom_punch_is_a_gated_constant():
    z = _zoom_expr(_zoom_items())
    assert z == "1+between(in_time,3.0,6.0)*0.15"


def test_zoom_uses_in_time_never_t():
    # zoompan has no `t` variable — an expression with bare t fails at runtime
    z = _zoom_expr(_zoom_items({"kind": "ease"}, {"start": 8.0, "end": 10.0, "kind": "drift"}))
    assert "in_time" in z and not _re.search(r"(?<![a-z_])t(?![a-z_(])", z)


def test_zoom_centres_are_time_gated_per_window():
    items = _zoom_items({}, {"start": 8.0, "end": 10.0, "cy": 0.35})
    cy = _centre_expr(items, "cy")
    assert "-0.1*between(in_time,3.0,6.0)" in cy  # 0.40 → offset −0.10 from base
    assert "-0.15*between(in_time,8.0,10.0)" in cy


def test_zoom_plan_rejects_overlap_and_wild_scale(tmp_path):
    p = tmp_path / "z.json"
    p.write_text(json.dumps({"zooms": [
        {"start": 1, "end": 5, "scale": 1.15}, {"start": 4, "end": 8, "scale": 1.15}]}))
    with pytest.raises(ToolError):
        _load_zoom_plan(p)
    p.write_text(json.dumps({"zooms": [{"start": 1, "end": 5, "scale": 2.5}]}))
    with pytest.raises(ToolError):
        _load_zoom_plan(p)


def test_zoom_plan_defaults_to_punch_at_emphasis_scale(tmp_path):
    p = tmp_path / "z.json"
    p.write_text(json.dumps({"zooms": [{"start": 1, "end": 5}]}))
    (it,) = _load_zoom_plan(p)
    assert it["kind"] == "punch" and it["scale"] == 1.18 and it["cy"] == 0.40


# --- storyboard (composition order, no ffmpeg) ---------------------------------

def test_storyboard_order_is_zooms_overlays_inserts():
    # geometry first, placement second, text on top — the load-bearing order
    assert [s for s, _, _ in _SB_SECTIONS] == ["zooms", "overlays", "inserts"]


def test_storyboard_refuses_two_texts_at_once(tmp_path):
    from chatmonteur.core import RunContext
    sb = tmp_path / "sb.json"
    sb.write_text(json.dumps({
        "inserts": [{"start": 24.7, "end": 28.2, "text": "монтаж одним промтом"}],
        "motion": [{"start": 25.4, "end": 29.7, "name": "callout"}],
    }, ensure_ascii=False), encoding="utf-8")
    ctx = RunContext.for_project(load_config(tmp_path), "t")
    with pytest.raises(ToolError, match="text layers overlap"):
        _SB_TOOL.run(ctx, input="x.mp4", storyboard=str(sb))


def test_storyboard_allows_texts_back_to_back():
    _sb_check_text({  # touching windows are fine — only true overlap is a clash
        "inserts": [{"start": 20.0, "end": 23.0, "text": "первая"}],
        "motion": [{"start": 23.0, "end": 27.0, "name": "callout"}],
    })


def test_storyboard_rejects_unknown_sections(tmp_path):
    from chatmonteur.core import RunContext
    sb = tmp_path / "sb.json"
    sb.write_text(json.dumps({"zoomz": []}))
    ctx = RunContext.for_project(load_config(tmp_path), "t")
    with pytest.raises(ToolError):
        _SB_TOOL.run(ctx, input="x.mp4", storyboard=str(sb))


def test_storyboard_empty_passes_video_through(tmp_path):
    from chatmonteur.core import RunContext
    sb = tmp_path / "sb.json"
    sb.write_text(json.dumps({"zooms": [], "inserts": []}))
    ctx = RunContext.for_project(load_config(tmp_path), "t")
    res = _SB_TOOL.run(ctx, input="x.mp4", storyboard=str(sb))
    assert res.artifacts["video"] == "x.mp4" and res.meta["sections"] == []


# --- sound (pure logic, no ffmpeg) ----------------------------------------------

def test_sfx_lands_before_its_beat():
    # hearing beats seeing — a hit on the exact frame reads as late
    assert _sfx_delay_ms(12.0) == 11985
    assert _sfx_delay_ms(0.0) == 0  # never negative at the head of the file


def test_sound_input_indexes_track_the_ffmpeg_order():
    # music carries its own -ss, so counting -i (not list length) is what maps
    # a file to its [N:a] label
    assert _snd_next_index(["video.mp4"]) == 1
    assert _snd_next_index(["video.mp4", "-ss", "12.0", "-i", "bed.mp3"]) == 2


def test_sound_plan_rejects_missing_file(tmp_path):
    with pytest.raises(ToolError):
        _load_sound_plan(str(tmp_path / "nope.json"))


# --- stock resolver (pure logic, no network) ------------------------------------

def test_stock_free_first_and_key_degradation(monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    assert _stock_providers("image", None) == ["openverse"]  # keyless survives
    assert _stock_providers("video", None) == []             # video needs a key
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    assert _stock_providers("video", None) == ["pexels"]
    assert _stock_providers("meme", None) == ["imgflip"]


def test_stock_forced_provider_must_serve_the_kind():
    with pytest.raises(ToolError):
        _stock_providers("video", "openverse")  # openverse has no video


def test_meme_matching_ranks_full_query_hits_first():
    memes = [{"name": "Drake Hotline Bling"}, {"name": "Distracted Boyfriend"},
             {"name": "Bling Empire"}]
    ranked = _match_memes(memes, "drake bling")
    assert ranked[0]["name"] == "Drake Hotline Bling"  # both tokens beat one
    assert [m["name"] for m in ranked] == ["Drake Hotline Bling", "Bling Empire"]
    # zero-hit templates are noise, not candidates — excluded entirely


# --- overlays (pure plan/graph generation, no ffmpeg) --------------------------

def test_overlay_plan_validates_pos_width_and_file(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    p = tmp_path / "o.json"
    p.write_text(json.dumps({"overlays": [
        {"start": 1, "end": 4, "file": str(img), "pos": "top_right", "width": 0.45}]}))
    (it,) = _load_ovl_plan(p)
    assert it["is_image"] and it["pos"] == "top_right"
    p.write_text(json.dumps({"overlays": [
        {"start": 1, "end": 4, "file": str(img), "pos": "bottom_center"}]}))
    with pytest.raises(ToolError):  # lower center belongs to captions/inserts
        _load_ovl_plan(p)
    p.write_text(json.dumps({"overlays": [
        {"start": 1, "end": 4, "file": str(img), "width": 0.9}]}))
    with pytest.raises(ToolError):  # would bury the speaker
        _load_ovl_plan(p)


def test_overlay_graph_scales_fades_and_gates(tmp_path):
    items = [{"file": "a.png", "start": 5.5, "end": 9.0, "pos": "top_right",
              "width": 0.45, "is_image": True}]
    g = _ovl_filter_graph(items, 1920, 1080)
    assert "scale=864:-2" in g                       # 45% of 1920, even
    assert "overlay=W-w-58:58" in g                  # top_right with 3% margin
    assert "enable='between(t,5.500,9.000)'" in g
    assert g.endswith("format=yuv420p[v]")


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
    expected = {"normalize", "transcribe", "cut_silence", "cut_edl", "subtitles", "inserts", "zooms", "overlays", "storyboard", "stock", "sound",
                "color", "motion", "render"}
    assert expected <= caps
