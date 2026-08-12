"""Fast guard tests (no ffmpeg). Run: pytest tests/test_core.py

These lock the contracts that make 'one command' safe: cut math, config
defaults, pipeline parsing, registry discovery, param resolution.
"""

from __future__ import annotations

import sys
import tomllib
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
from chatmonteur.tools.overlays import TOOL as _OVL_TOOL  # noqa: E402
from chatmonteur.tools.sound import _load_plan as _load_sound_plan  # noqa: E402
from chatmonteur.tools.sound import _next_input_index as _snd_next_index  # noqa: E402
from chatmonteur.tools.sound import _sfx_delay_ms  # noqa: E402
from chatmonteur.tools.stock import _match_memes  # noqa: E402
from chatmonteur.tools.stock import _providers_for as _stock_providers  # noqa: E402
from chatmonteur.tools.motion_hyperframes import _resolve as _hf_resolve  # noqa: E402
from chatmonteur.tools.qc import _expected_seconds as _qc_expected  # noqa: E402
from chatmonteur.tools.qc import _judge as _qc_judge  # noqa: E402
from chatmonteur.tools.storyboard import _SECTIONS as _SB_SECTIONS  # noqa: E402
from chatmonteur.tools.storyboard import TOOL as _SB_TOOL  # noqa: E402
from chatmonteur.tools.storyboard import _check_one_text_at_a_time as _sb_check_text  # noqa: E402
from chatmonteur.tools.storyboard import _covered as _sb_covered  # noqa: E402
from chatmonteur.tools.storyboard import _longest_gap as _sb_longest_gap  # noqa: E402
from chatmonteur.tools.storyboard import _thin_spots as _sb_thin  # noqa: E402
from chatmonteur.tools.storyboard import _unjustified_zooms as _sb_zoom_reasons  # noqa: E402
from chatmonteur.tools.transcribe_whisper import _apply_fixes as _asr_fix  # noqa: E402
from chatmonteur.tools.transcribe_whisper import _check_language as _asr_lang  # noqa: E402
from chatmonteur.tools.transcribe_whisper import _drop_hallucinations as _asr_drop  # noqa: E402
from chatmonteur.tools.transcribe_whisper import _split_token as _asr_split  # noqa: E402
from chatmonteur.tools.transitions import _check_discipline as _tr_discipline  # noqa: E402
from chatmonteur.tools.transitions import _check_room as _tr_room  # noqa: E402
from chatmonteur.tools.transitions import _default_duration as _tr_default_dur  # noqa: E402
from chatmonteur.tools.transitions import _effective as _tr_effective  # noqa: E402
from chatmonteur.tools.transitions import _graph as _tr_graph  # noqa: E402
from chatmonteur.tools.transitions import _normalise_joins as _tr_joins  # noqa: E402
from chatmonteur.tools.transitions import _offsets as _tr_offsets  # noqa: E402
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


def _breathing(line: str, pause_after: str, pause: float) -> dict:
    words, t = [], 0.0
    for tok in line.split():
        words.append({"start": round(t, 2), "end": round(t + 0.32, 2), "word": " " + tok})
        t += 0.38 + (pause if tok == pause_after else 0.0)
    return {"segments": [{"start": 0.0, "end": t, "text": line, "words": words}]}


def test_a_cue_breaks_where_the_speaker_breathes():
    # no punctuation marks this break — only the 0.45s gap does
    data = _breathing("и вот здесь начинается самое интересное во всей истории", "начинается", 0.45)
    cues = _build_cues(data, 39)
    assert [c["text"] for c in cues] == [
        "и вот здесь начинается", "самое интересное во всей истории"]


def test_a_pause_does_not_shred_a_cue_that_has_not_earned_its_time():
    # the gap lands after 0.7s of speech — below the minimum a cue must hold,
    # so the phrase stays whole rather than flashing two words on screen
    data = _breathing("сначала это потом всё остальное по порядку", "это", 0.45)
    assert len(_build_cues(data, 39)) == 1


def _ass(variant, font="Golos Text"):
    return _to_ass(_SUBS, 42, 1920, 1080, font, variant)


def test_variant_clean_has_no_per_word_motion():
    assert "\\t(" not in _ass("clean")  # C is a static line


def test_variant_read_aloud_fades_each_word():
    ass = _ass("read_aloud")
    assert ass.count("\\t(") == 4 and "\\alpha&HFF&" in ass  # 4 words, each fades in


def test_variant_accent_inverts_only_the_emph_word():
    """Card 04 accents by inversion; the brandbook rule is colour never carries text."""
    ass = _ass("accent")
    assert ass.count("\\1c&H0D0B0B&") == 1            # exactly one word flips to ink
    assert ass.count("\\3c&HF7FAFA&\\3a&H00&") == 1   # on an opaque paper chip
    # no caption colour survives: the retired yellow, and the green before it
    assert "&H00D7FF&" not in ass and "&H6AE82B&" not in ass


def test_variant_typewriter_is_mono_with_cursor():
    ass = _ass("typewriter", font="JetBrains Mono")
    assert "JetBrains Mono" in ass and "▌" in ass and "\\t(" in ass


def test_every_variant_sits_on_the_scrim():
    """BorderStyle 3 is the scrim: OutlineColour fills the box, Outline pads it."""
    for variant in ("clean", "accent", "highlight", "read_aloud", "typewriter"):
        ass = _ass(variant)
        style = next(l for l in ass.splitlines() if l.startswith("Style: Default"))
        parts = style.split(",")
        outline_colour, border_style, outline = parts[5], parts[15], parts[16]
        assert outline_colour == "&H7A0A0908", variant   # ink at 52%, card 04
        assert border_style == "3" and int(outline) >= 2, variant


def test_variant_highlight_chips_each_word_in_turn():
    ass = _ass("highlight")
    assert ass.count("\\1c&H0D0B0B&") == 4   # every word takes the chip at its time
    assert ass.count("\\1c&HF7FAFA&") == 4   # and returns to paper-on-scrim after
    # returning restores the scrim's own box — \bord0 would punch a hole in the band
    assert "\\bord0" not in ass


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
    # half-open gate [s, e): between() includes both ends, so back-to-back
    # windows would ADD their scales for one frame right on the cut
    z = _zoom_expr(_zoom_items())
    assert z == "1+(gte(in_time,3.0)*lt(in_time,6.0))*0.15"


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
    expected = {"normalize", "transcribe", "cut_silence", "cut_edl", "redact", "subtitles", "inserts", "zooms", "overlays", "storyboard", "stock", "sound",
                "color", "motion", "render", "qc", "transitions"}
    assert expected <= caps


def test_overlay_declares_its_pillow_runtime_dependency():
    assert "PIL" in _OVL_TOOL.manifest.requires_py


def test_fresh_setup_and_dev_install_include_pillow():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dev = [dep.lower() for dep in project["optional-dependencies"]["dev"]]
    assert any(dep.startswith("pillow") for dep in dev)
    for script in ("setup.ps1", "setup.sh"):
        assert ".[whisper,emoji]" in (root / script).read_text(encoding="utf-8")
    assert ".[whisper,emoji,dev]" in (root / "CONTRIBUTING.md").read_text(encoding="utf-8")


def test_every_capability_is_routed_in_the_skill():
    """A capability the agent never reads about is a capability the project doesn't have.

    Only seven steps run from the pipeline; the rest are called by the agent from
    `skills/montage.md`. When that table went stale, `sound` and `transitions` shipped
    fully tested and completely unreachable — which is how a session ends with nothing
    but cut pauses and subtitles. This fails until a new capability is documented.
    """
    caps = set(ToolRegistry().discover()._by_capability)
    doc = (Path(__file__).resolve().parents[1] / "skills" / "montage.md").read_text(encoding="utf-8")
    named = set(_re.findall(r"`([a-z_]+)`", doc))
    assert not (caps - named), f"not routed in skills/montage.md: {sorted(caps - named)}"


# --- qc: the rule set that blocks a broken render (pure, no ffmpeg) ------------

def _facts(**over) -> dict:
    """A file that passes everything, so each test can break exactly one thing."""
    base = {"readable": True, "duration": 80.0, "width": 1920, "height": 1080,
            "has_audio": True, "mean_volume_db": -17.2, "max_volume_db": -2.3,
            "frame_luma": {"10%": 88.0, "35%": 86.8, "65%": 89.4, "90%": 88.0}}
    return {**base, **over}


def _checks(issues) -> set[str]:
    return {i["check"] for i in issues if i["severity"] == "fail"}


def test_qc_passes_a_healthy_render():
    assert _qc_judge(_facts(), expected=80.0) == []


def test_qc_black_frame_threshold_clears_broadcast_black():
    # limited-range black is Y=16 EXACTLY, so a `< 16` test would never fire;
    # measured brand background #0B0B0C sits at 26 and must stay legal
    assert "black_frame" in _checks(_qc_judge(_facts(frame_luma={"10%": 16.0}), 80.0))
    assert "black_frame" not in _checks(_qc_judge(_facts(frame_luma={"10%": 26.0}), 80.0))


def test_qc_blocks_silence_and_clipping():
    assert "silent" in _checks(_qc_judge(_facts(mean_volume_db=-91.0), 80.0))
    assert "clipping" in _checks(_qc_judge(_facts(max_volume_db=0.0), 80.0))


def test_qc_blocks_missing_audio_and_unreadable_container():
    assert "no_audio" in _checks(_qc_judge(_facts(has_audio=False), 80.0))
    assert _checks(_qc_judge({"readable": False}, 80.0)) == {"container"}


def test_qc_blocks_partial_decode():
    # fewer probe frames than positions means the file is damaged mid-way
    assert "undecodable" in _checks(_qc_judge(_facts(frame_luma={"10%": 88.0}), 80.0))


def test_qc_duration_drift_blocks_only_past_the_tolerance():
    assert _checks(_qc_judge(_facts(duration=90.0), 80.0)) == set()          # +12.5 %
    assert "duration_drift" in _checks(_qc_judge(_facts(duration=40.0), 80.0))  # −50 %


def test_qc_warns_when_runtime_went_unchecked():
    issues = _qc_judge(_facts(), expected=None)
    assert _checks(issues) == set()  # a missing reference must not block a good file
    assert [i["check"] for i in issues] == ["duration_drift"]


def test_qc_expected_accepts_seconds_or_a_path():
    assert _qc_expected(12.5) == 12.5
    assert _qc_expected("12.5") == 12.5
    assert _qc_expected(None) is None
    assert _qc_expected("no/such/file.mp4") is None


# --- storyboard: the boringness review (pure, no ffmpeg) ----------------------

def test_thin_plan_with_no_events_is_refused():
    (found,) = _sb_thin({}, duration=300.0)
    assert "no visual events" in found


def test_thin_plan_flags_a_dead_stretch():
    # events crowded into the first 20s, then four minutes of nothing
    plan = {"zooms": [{"start": 2, "end": 6}, {"start": 12, "end": 18}]}
    (found,) = _sb_thin(plan, duration=260.0)
    assert "nothing happening" in found and "242s" in found


def test_evenly_spread_events_pass_the_review():
    # scale alternates: bare {start, end} zooms all inherit the SAME default
    # framing, which the repetition rule correctly reads as a rut
    plan = {"zooms": [{"start": s, "end": s + 4, "scale": 1.18 + 0.06 * (i % 2)}
                      for i, s in enumerate(range(5, 300, 60))]}
    assert _sb_thin(plan, duration=300.0) == []


def test_text_heavy_plan_reads_as_animated_slides():
    plan = {"zooms": [{"start": s, "end": s + 3} for s in range(0, 100, 20)],
            "inserts": [{"start": s, "end": s + 8, "text": f"строка {s}"} for s in range(0, 100, 10)]}
    assert any("animated slides" in f for f in _sb_thin(plan, duration=100.0))


def test_repeated_captions_are_flagged():
    plan = {"inserts": [{"start": s, "end": s + 3, "text": "то же самое"} for s in range(0, 80, 20)]}
    assert any("distinct captions" in f for f in _sb_thin(plan, duration=85.0))


def test_three_identical_zooms_in_a_row_are_a_rut():
    same = {"kind": "punch", "scale": 1.18, "cx": 0.5, "cy": 0.4}
    plan = {"zooms": [{**same, "start": s, "end": s + 4} for s in (5, 25, 45)]}
    assert any("identical zooms" in f for f in _sb_thin(plan, duration=60.0))
    varied = [{**same, "start": 5, "end": 9}, {**same, "scale": 1.3, "start": 25, "end": 29},
              {**same, "start": 45, "end": 49}]
    assert not any("identical zooms" in f for f in _sb_thin({"zooms": varied}, duration=60.0))


def test_longest_gap_counts_the_head_and_the_tail():
    # dead air before the first event is dead air in the hook
    assert _sb_longest_gap([{"start": 40, "end": 45}], 60.0) == (0.0, 40.0)
    assert _sb_longest_gap([{"start": 2, "end": 5}], 60.0) == (5.0, 60.0)


def test_covered_counts_an_overlap_once():
    assert _sb_covered([{"start": 0, "end": 10}, {"start": 5, "end": 12}]) == 12.0


# --- transitions (pure; the ffmpeg run is verified on the bench) --------------

def test_xfade_offsets_measure_against_the_composed_timeline():
    # THE bug this guards: every transition SHORTENS the timeline, so offset i is
    # measured after i-1 joins. Summing raw durations puts join #2 at 12.967 and
    # drifts a little more at every seam after it.
    joins = [{"duration": 0.4}, {"duration": 1 / 30}]
    a, b = _tr_offsets([3.0, 10.0, 5.0], joins)
    assert a == 2.6
    assert round(b, 3) == 12.567


def test_transition_length_scales_with_runtime():
    assert _tr_default_dur(40) == 0.4      # a short wants a quick dissolve
    assert _tr_default_dur(300) == 0.75
    assert _tr_default_dur(1800) == 1.2    # a long talk can breathe


def test_joins_default_to_hard_cuts_and_reject_nonsense():
    joins = _tr_joins([{"kind": "crossfade"}], count=3, runtime=40.0)
    assert [j["kind"] for j in joins] == ["crossfade", "cut", "cut"]
    assert joins[0]["duration"] == 0.4 and joins[1]["duration"] == 0.0
    with pytest.raises(ToolError, match="unknown kind"):
        _tr_joins([{"kind": "starwipe"}], 1, 40.0)
    with pytest.raises(ToolError, match="sane range"):
        _tr_joins([{"kind": "fade", "duration": 9.0}], 1, 40.0)


def test_audio_may_lead_the_picture():
    (j,) = _tr_joins([{"kind": "crossfade", "duration": 0.4, "audio_duration": 1.0}], 1, 40.0)
    assert j["duration"] == 0.4 and j["audio_duration"] == 1.0


def test_scattered_transitions_are_refused():
    scattered = [{"kind": k} for k in ("cut", "fade", "crossfade")]
    with pytest.raises(ToolError, match="scattered"):
        _tr_discipline(scattered, log=lambda m: None, allow_scattered=False)
    disciplined = [{"kind": k} for k in ("cut", "cut", "crossfade")]
    _tr_discipline(disciplined, log=lambda m: None, allow_scattered=False)
    # under three joins there is no pattern to judge
    _tr_discipline([{"kind": "fade"}, {"kind": "cut"}], log=lambda m: None, allow_scattered=False)


def test_transition_may_not_eat_half_the_shorter_clip():
    clips = [{"duration": 3.0}, {"duration": 10.0}]
    _tr_room(clips, [{"duration": 1.5, "audio_duration": 1.5}])
    with pytest.raises(ToolError, match="too much for clips"):
        _tr_room(clips, [{"duration": 2.0, "audio_duration": 2.0}])
    # a long audio lead counts against the same budget
    with pytest.raises(ToolError, match="too much for clips"):
        _tr_room(clips, [{"duration": 0.4, "audio_duration": 2.0}])


def test_hard_cuts_stay_exact_unless_the_chain_blends():
    cuts = [{"kind": "cut", "duration": 0.0}] * 2
    assert _tr_effective(cuts, 30.0) == cuts             # concat path: no frame spent
    mixed = [{"kind": "fade", "duration": 0.4}, {"kind": "cut", "duration": 0.0}]
    assert _tr_effective(mixed, 30.0)[1]["duration"] == pytest.approx(1 / 30)


def _clip(dur, audio=True):
    return {"file": "c.mp4", "duration": dur, "width": 1920, "height": 1080,
            "fps": 30.0, "has_audio": audio}


def test_graph_gives_a_silent_clip_a_real_audio_track():
    # a HyperFrames title card carries no audio, and acrossfade/concat break on it
    info = [_clip(3.0, audio=False), _clip(10.0)]
    graph, silent = _tr_graph(info, [{"kind": "cut", "duration": 0.0}], 1920, 1080, 30.0)
    assert silent == [0]
    assert "[2:a]aresample=48000" in graph  # input 2 = the anullsrc appended after the clips
    assert "[1:a]aresample=48000" in graph


def test_all_cut_timeline_uses_concat_not_xfade():
    info = [_clip(3.0), _clip(10.0)]
    graph, _ = _tr_graph(info, [{"kind": "cut", "duration": 0.0}], 1920, 1080, 30.0)
    assert "concat=n=2:v=1:a=1[v][a]" in graph and "xfade" not in graph


def test_blended_timeline_chains_xfade_and_acrossfade():
    info = [_clip(3.0), _clip(10.0)]
    joins = [{"kind": "fade", "duration": 0.4, "audio_duration": 0.4}]
    graph, _ = _tr_graph(info, joins, 1920, 1080, 30.0)
    assert "xfade=transition=fadeblack" in graph and "offset=2.6000" in graph
    assert "acrossfade=d=0.4000" in graph


# --- ASR cleanup: what must never reach a caption -----------------------------

_FIXES = {"клод код": "Claude Code", "опен роутер": "OpenRouter", "гермес": "Hermes",
          "обс": "OBS", "иимерсивный": "ИИмерсивный"}


def _spoken(sentence: str) -> list[dict]:
    words, t = [], 0.0
    for w in sentence.split(" "):
        words.append({"start": round(t, 2), "end": round(t + 0.3, 2), "word": " " + w, "prob": 0.9})
        t += 0.35
    return words


def _seg(text, start=0.0, end=1.0, no_speech=0.02, logprob=-0.3):
    return {"start": start, "end": end, "text": text, "words": [],
            "no_speech_prob": no_speech, "avg_logprob": logprob}


def test_english_only_model_would_translate_not_transcribe():
    # the failure that looks like success: fluent English output from Russian audio
    with pytest.raises(ToolError, match="TRANSLATE"):
        _asr_lang("large-v3.en", "ru")
    _asr_lang("medium.en", "en")
    _asr_lang("large-v3", "ru")


def test_plausible_hallucination_over_silence_is_dropped():
    # "Подписывайтесь на канал" is ordinary Russian — no pattern catches it.
    # Whisper's own no_speech_prob/avg_logprob do.
    real = [_seg(f"реплика {i}") for i in range(8)]
    invented = _seg("Подписывайтесь на канал", no_speech=0.91, logprob=-1.7)
    kept, dropped = _asr_drop(real + [invented], "large-v3")
    assert dropped == 1 and all("Подписывайтесь" not in s["text"] for s in kept)


def test_undecodable_characters_take_the_whole_segment():
    # the real dogfood failure: "СИГНАЛ СМС" burned into a caption
    real = [_seg(f"реплика {i}") for i in range(8)]
    kept, dropped = _asr_drop(real + [_seg("СИГНАЛ СМС �")], "large-v3")
    assert dropped == 1 and all("СИГНАЛ" not in s["text"] for s in kept)


def test_notes_and_micro_fillers_go_but_real_speech_stays():
    segs = [_seg("реальная речь"), _seg("♪♪♪"), _seg(""), _seg("эм", 0.0, 0.05)]
    segs += [_seg(f"ещё {i}") for i in range(6)]
    kept, dropped = _asr_drop(segs, "large-v3")
    assert dropped == 3 and kept[0]["text"] == "реальная речь"


def test_a_mostly_hallucinated_transcript_fails_instead_of_being_patched():
    junk = [_seg("♪"), _seg("♪ ♪"), _seg("�"), _seg("реальная речь")]
    with pytest.raises(ToolError, match="transcription failed"):
        _asr_drop(junk, "small")


def test_brand_fixes_span_words_and_keep_punctuation():
    line = "Ставим клод код через опен роутер, потом гермес."
    seg = [{"start": 0, "end": 5, "text": line, "words": _spoken(line)}]
    fixed, n = _asr_fix(seg, _FIXES)
    assert fixed[0]["text"] == "Ставим Claude Code через OpenRouter, потом Hermes."
    assert n == 3


def test_a_corrected_phrase_collapses_into_one_timed_token():
    # "опен роутер" (2 words) -> "OpenRouter" (1): the token must carry the whole span
    line = "через опен роутер дальше"
    seg = [{"start": 0, "end": 2, "text": line, "words": _spoken(line)}]
    fixed, _ = _asr_fix(seg, _FIXES)
    token = next(w for w in fixed[0]["words"] if "OpenRouter" in w["word"])
    assert (token["start"], token["end"]) == (0.35, 1.0)


def test_a_spelling_the_dictionary_confirms_is_not_counted_as_a_fix():
    line = "канал ИИмерсивный"
    seg = [{"start": 0, "end": 1, "text": line, "words": _spoken(line)}]
    _, n = _asr_fix(seg, _FIXES)
    assert n == 0


def test_fixes_reach_segments_that_have_no_word_timings():
    seg = [{"start": 0, "end": 1, "text": "запускаю гермес", "words": []}]
    fixed, n = _asr_fix(seg, _FIXES)
    assert fixed[0]["text"] == "запускаю Hermes" and n == 1


def test_split_token_keeps_the_pieces_apart():
    assert _asr_split(" «клод»,") == (" ", "«", "клод", "»,")
    assert _asr_split("обс") == ("", "", "обс", "")


# --- motion: hyperframes takes a DIRECTORY, not a file ------------------------

def test_composition_path_splits_into_project_dir_and_file(tmp_path):
    # `hyperframes render <file.html>` fails with "Not a directory"
    (tmp_path / "index.html").write_text("<div></div>")
    (tmp_path / "lower.html").write_text("<div></div>")
    assert _hf_resolve(str(tmp_path)) == (tmp_path, None)
    assert _hf_resolve(str(tmp_path / "index.html")) == (tmp_path, None)
    assert _hf_resolve(str(tmp_path / "lower.html")) == (tmp_path, "lower.html")
    with pytest.raises(ToolError, match="composition not found"):
        _hf_resolve(str(tmp_path / "missing.html"))


# --- brand: one source of truth, swappable ------------------------------------

def test_brand_loader_reproduces_every_hardcoded_value():
    """Wiring the tools to the loader must not change a single pixel.

    These are the exact literals the tools carry today. If tokens.css and the code
    ever disagree, the captions ship the stale colour and nobody notices until it
    is on YouTube.
    """
    from chatmonteur import brand
    assert brand.ass("caption-accent") == "&H00D7FF&"  # subtitles _ACCENTS["yellow"]
    assert brand.ass("paper") == "&HF7FAFA&"           # subtitles _PAPER_C
    assert brand.ass("paper", alpha=0) == "&H00F7FAFA"  # subtitles/inserts _PAPER
    assert brand.ass("ink", alpha=0) == "&H000C0B0B"   # inserts _INK
    assert brand.font("sans") == "Golos Text"
    assert brand.font("mono") == "JetBrains Mono"
    assert brand.font_dir().is_dir()


def test_cold_open_outline_text_is_painted_for_hyperframes_check():
    """An outlined headline must not use a transparent fill that the layout gate rejects."""
    component = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "brand"
        / "default"
        / "components"
        / "mono-39"
        / "index.html"
    ).read_text(encoding="utf-8")
    assert 'id="m39-a-text"' in component
    assert "color:transparent;-webkit-text-stroke:5px #FAFAF7" not in component
    assert "color:#0B0B0C;-webkit-text-stroke:5px #FAFAF7" in component


def test_ass_colour_is_byte_reversed():
    """libass stores colour as BGR. Reversing by hand is how green ships as blue."""
    from chatmonteur import brand
    assert brand.colour("accent-hype") == "#FF5B2E"
    assert brand.ass("accent-hype") == "&H2E5BFF&"


def test_brand_is_swappable_without_touching_code(tmp_path, monkeypatch):
    """A new brand book = a new folder with a tokens.css. That is the whole contract."""
    from chatmonteur import brand
    root = tmp_path / "brands"
    (root / "newbook").mkdir(parents=True)
    (root / "newbook" / "tokens.css").write_text(
        ":root{--accent:#FF0000;--font-sans:'Inter', sans-serif;}", encoding="utf-8")
    monkeypatch.setattr(brand, "_BRAND_ROOT", root)
    brand.tokens.cache_clear()
    assert brand.colour("accent", brand="newbook") == "#FF0000"
    assert brand.ass("accent", brand="newbook") == "&H0000FF&"
    assert brand.font("sans", brand="newbook") == "Inter"
    brand.tokens.cache_clear()


def test_unknown_brand_and_token_fail_loudly():
    from chatmonteur import brand
    with pytest.raises(ToolError, match="no tokens.css"):
        brand.tokens("nosuchbrand")
    with pytest.raises(ToolError, match="no token"):
        brand.token("nosuchtoken")
    with pytest.raises(ToolError, match="not a #RRGGBB"):
        brand.colour("font-sans")


def test_sfx_gain_outside_sane_range_is_refused(tmp_path):
    # an agent plan with SFX louder than dialogue must fail, not mix silently
    from chatmonteur.core import RunContext
    from chatmonteur.tools.sound import TOOL as _SND_TOOL
    wav = tmp_path / "hit.wav"
    wav.write_bytes(b"RIFF")  # existence is all the guard needs before it validates gain
    ctx = RunContext.for_project(load_config(tmp_path), "t")
    with pytest.raises(ToolError, match="sane range"):
        _SND_TOOL.run(ctx, input="x.mp4", sfx=[{"at": 1.0, "file": str(wav), "gain_db": 6}])


def test_overlay_blur_backdrop_wraps_the_window():
    # evidence card: blurred LIVE base under the card, only inside the window
    g = _ovl_filter_graph([{"file": "x.png", "start": 2.0, "end": 5.0, "pos": "center",
                            "width": 0.6, "is_image": True, "backdrop": "blur"}], 1920, 1080)
    assert "boxblur" in g and "(W-w)/2" in g and "(H-h)/2" in g
    assert "enable='between(t,2.000,5.000)'" in g
    plain = _ovl_filter_graph([{"file": "x.png", "start": 2.0, "end": 5.0, "pos": "top_right",
                                "width": 0.4, "is_image": True, "backdrop": None}], 1920, 1080)
    assert "boxblur" not in plain  # blur is opt-in, never a side effect


def test_card_mockup_rounds_and_shadows(tmp_path):
    # the reference technique: ONE card style for every screenshot
    from PIL import Image
    from chatmonteur.tools.overlays import _make_card
    src = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), (200, 60, 60)).save(src)
    dst = tmp_path / "card.png"
    _make_card(str(src), dst)
    out = Image.open(dst)
    assert out.size[0] > 400 and out.size[1] > 300          # shadow margin added
    assert out.getpixel((0, 0))[3] == 0                     # corner is transparent
    cx, cy = out.size[0] // 2, out.size[1] // 2
    assert out.getpixel((cx, cy))[3] == 255                 # content fully opaque


def test_card_on_video_is_refused(tmp_path):
    clip = tmp_path / "b.mp4"; clip.write_bytes(b"x")
    with pytest.raises(ToolError, match="card"):
        _load_ovl_plan(_write_plan(tmp_path, {"overlays": [
            {"start": 0, "end": 2, "file": str(clip), "card": True}]}))


def _write_plan(tmp_path, data):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# --- cues: the brand gate ------------------------------------------------------
#
# The manifest's numbers are only worth writing down if something refuses to
# render the plan that breaks them. These test the refusals, not the ffmpeg.

from chatmonteur.tools.cues import _check, _load_brand, _resolve, _variables  # noqa: E402


def _plan(*cues):
    catalog, _ = _load_brand()
    return _resolve(list(cues), catalog)


def _gate(plan, duration=600.0, allow_thin=True):
    _, manifest = _load_brand()
    _check(plan, manifest, duration=duration, log=lambda *_: None, allow_thin=allow_thin)


def test_cue_rejects_unknown_and_unbuilt_elements():
    with pytest.raises(ToolError, match="unknown element"):
        _plan({"t": 1, "element": "99", "text": "x"})
    # 22 and 30 are named by the manifest but the designer never drew them, so the
    # agent is right to expect them and deserves better than «unknown element»
    with pytest.raises(ToolError, match="never drew a card"):
        _plan({"t": 1, "element": "22", "text": "x"})


def test_cue_text_fills_declared_variables_in_order():
    plan = _plan({"t": 12.4, "element": "03",
                  "text": ["Джулиан Иванов", "AI Automation · автор"]})
    assert plan[0]["vars"] == {"name": "Джулиан Иванов", "role": "AI Automation · автор"}


def test_cue_refuses_to_guess_which_line_goes_where():
    """A wrong guess renders a plausible card that says the wrong thing."""
    with pytest.raises(ToolError, match=r"needs 2 value"):
        _plan({"t": 1, "element": "03", "text": "Джулиан Иванов"})


def test_cue_highlight_word_splits_the_line():
    plan = _plan({"t": 84.2, "element": "B", "text": "это абсолютно бесплатно",
                  "highlightWord": "бесплатно"})
    assert plan[0]["vars"] == {"pre": "это абсолютно", "word": "бесплатно", "post": ""}


def test_cue_highlight_word_needs_a_splitting_element():
    with pytest.raises(ToolError, match="pre/word/post"):
        _plan({"t": 1, "element": "03", "text": "имя", "highlightWord": "имя"})


def test_cue_vars_typo_names_the_real_variables():
    with pytest.raises(ToolError, match=r"declares \['name', 'role'\]"):
        _plan({"t": 1, "element": "03", "vars": {"naem": "x", "role": "y"}})


def test_gate_refuses_two_cues_on_screen_at_once():
    with pytest.raises(ToolError, match="share the screen"):
        _gate(_plan({"t": 10, "element": "03", "text": ["a", "b"], "holdSec": 5},
                    {"t": 12, "element": "15", "vars": {}, "holdSec": 5}))


def test_gate_caps_the_loud_accents():
    cues = [{"t": 30.0 * i, "element": "A", "text": "бум"} for i in range(1, 6)]
    with pytest.raises(ToolError, match="loud accents"):
        _gate(_plan(*cues))


def test_gate_keeps_accents_apart():
    with pytest.raises(ToolError, match="apart"):
        _gate(_plan({"t": 10, "element": "A", "text": "раз"},
                    {"t": 25, "element": "A", "text": "два"}))


def test_gate_allows_only_one_kind_of_transition():
    with pytest.raises(ToolError, match="kinds of transition"):
        _gate(_plan({"t": 10, "element": "07A", "text": ["ГЛАВА 2", "Настройка"]},
                    {"t": 60, "element": "07B", "vars": {}}))


def test_gate_counts_accents_per_ten_minutes():
    cues = [{"t": 30.0 * i, "element": "B", "text": "это очень важно",
             "highlightWord": "важно"} for i in range(1, 11)]
    with pytest.raises(ToolError, match="ceiling for a film"):
        _gate(_plan(*cues), duration=600.0)


def test_gate_does_not_extrapolate_a_short_clip_into_a_violation():
    """One accent in a 30s clip is one accent, not «twenty per ten minutes»."""
    _gate(_plan({"t": 5, "element": "B", "text": "это важно", "highlightWord": "важно"}),
          duration=30.0, allow_thin=False)


def test_gate_lets_a_quiet_film_through_only_on_purpose():
    plan = _plan({"t": 10, "element": "B", "text": "это важно", "highlightWord": "важно"})
    with pytest.raises(ToolError, match="allow_thin"):
        _gate(plan, duration=600.0, allow_thin=False)
    _gate(plan, duration=600.0, allow_thin=True)      # said out loud: fine


def test_gate_refuses_a_cue_held_past_the_ceiling():
    with pytest.raises(ToolError, match="ceiling"):
        _gate(_plan({"t": 10, "element": "03", "text": ["a", "b"], "holdSec": 9}))


def test_filter_path_escapes_what_would_split_a_filter_argument():
    """A folder named «Renders, final» must not read as two filter arguments."""
    from chatmonteur.media import filter_path

    assert filter_path(r"C:\Renders, final\sub.ass") == r"C\:/Renders\, final/sub.ass"
    assert filter_path(r"C:\a[1]\b;c\f.ass") == r"C\:/a\[1\]/b\;c/f.ass"


def test_filter_path_refuses_a_quote_it_cannot_escape():
    """Callers wrap the result in '...'; ffmpeg has no escape for a quote inside."""
    from chatmonteur.media import filter_path

    with pytest.raises(ValueError, match="single quote"):
        filter_path(r"C:\Users\Bob's PC\fonts")


def test_gate_refuses_a_card_cut_shorter_than_the_designer_drew_it():
    with pytest.raises(ToolError, match="needs 4.0s"):
        _gate(_plan({"t": 10, "element": "A", "text": "бум", "holdSec": 1.5}))


def test_gate_charges_reading_time_for_text_beyond_the_drawn_card():
    """A paragraph poured into a card drawn for a phrase buys 0.2s per extra word."""
    long_text = "это очень важно " * 5          # 15 words where the card drew ~3
    plan = _plan({"t": 10, "element": "B", "text": long_text.strip(),
                  "highlightWord": "важно", "holdSec": 4.0})
    with pytest.raises(ToolError, match="needs"):
        _gate(plan)
    _gate(_plan({"t": 10, "element": "B", "text": long_text.strip(),
                 "highlightWord": "важно", "holdSec": 7.0}))


def test_zoom_reason_advises_when_the_move_only_follows_movement():
    """Murch's bottom three justify a move the least — say so, but never block it."""
    notes = _sb_zoom_reasons({"zooms": [
        {"start": 10, "reason": "story"},          # top three: silent
        {"start": 20, "reason": "eye_trace"},      # weakest tier
        {"start": 30},                             # no reason at all
    ]})
    assert len(notes) == 2
    assert "eye_trace" in notes[0] and "20s" in notes[0]
    assert "no reason" in notes[1]


def test_screencast_needs_a_real_reset_not_a_zoom():
    """Zooming the same screen is the same screen, closer — it resets nothing."""
    zoom_only = {"material": "screencast",
                 "zooms": [{"start": t, "end": t + 3} for t in range(0, 300, 30)]}
    assert any("no reset" in f for f in _sb_thin(zoom_only, 300.0))

    # one real graphic in the middle breaks the stretch into two survivable halves
    with_reset = dict(zoom_only, inserts=[{"start": 150, "end": 154, "text": "глава 2"}])
    assert not any("no reset" in f for f in _sb_thin(with_reset, 300.0))

    # talking-head material is not judged on the tutorial clock
    assert not any("no reset" in f for f in _sb_thin(dict(zoom_only, material="talking_head"), 300.0))


def test_levelling_gain_targets_the_peak_and_ignores_a_pointless_nudge():
    """The cut threshold needs a predictable peak; anything under 0.5 dB is noise."""
    import chatmonteur.tools.normalize as _nz

    def _peak(value):
        return lambda _src: {"max": value} if value is not None else {}

    orig = _nz.media.volume_stats
    try:
        _nz.media.volume_stats = _peak(-9.3)
        assert _nz._levelling_gain("x.mov", log=lambda m: None) == pytest.approx(8.3)
        _nz.media.volume_stats = _peak(-1.2)          # already at level
        assert _nz._levelling_gain("x.mov", log=lambda m: None) == 0.0
        _nz.media.volume_stats = _peak(None)          # no readable audio
        assert _nz._levelling_gain("x.mov", log=lambda m: None) == 0.0
    finally:
        _nz.media.volume_stats = orig


def test_levelling_refuses_to_amplify_a_silent_track():
    """Артур's OBS track 1 is a silent desktop feed at −91 dBFS: +90 dB of gain
    applied to the voice track beside it is the accident this prevents."""
    import chatmonteur.tools.normalize as _nz

    said = []
    orig = _nz.media.volume_stats
    try:
        _nz.media.volume_stats = lambda _src: {"max": -91.0}
        assert _nz._levelling_gain("obs.mkv", log=said.append) == 0.0
        assert any("silence" in m for m in said)
    finally:
        _nz.media.volume_stats = orig


def test_two_pass_loudnorm_falls_back_when_measurement_fails():
    """A slightly compressed render beats no render — but it must say so."""
    import chatmonteur.tools.render as _rd

    said = []
    orig = _rd._measure
    try:
        _rd._measure = lambda src, base, log: {}
        f = _rd._loudnorm_filter("x.mov", -14.0, log=said.append)
        assert f == "loudnorm=I=-14.0:TP=-1.5:LRA=11"
        assert any("falling back" in m for m in said)
    finally:
        _rd._measure = orig


def test_card_backdrop_is_dimmed_not_merely_blurred():
    """Артур 2026-08-01: «фон размыт И притемнён». Blur alone was shipping a bright
    saturated plate under the card — visible the moment a real frame was looked at.
    colorlevels must use the OUTPUT max (romax); the input form brightens instead."""
    from chatmonteur.tools.overlays import _filter_graph, _BACKDROP_DIM

    g = _filter_graph([{
        "start": 1.0, "end": 4.0, "pos": "center", "width": 0.6,
        "backdrop": "blur", "is_image": True, "card": True,
    }], 1920, 1080)
    assert "boxblur" in g
    assert f"romax={_BACKDROP_DIM}" in g and "rimax=" not in g
    assert "saturation=" in g
    assert _BACKDROP_DIM < 1.0


def test_contact_sheet_orders_every_section_by_time():
    """The sheet is read top to bottom in a minute — so it is one time-ordered
    list, not four sections the reviewer has to interleave in their head."""
    import chatmonteur.tools.contact_sheet as _cs

    beats = _cs._beats({
        "inserts": [{"start": 30, "end": 33, "text": "вот так"}],
        "zooms": [{"start": 5, "end": 9, "kind": "punch", "scale": 1.2, "reason": "story"}],
        "overlays": [{"start": 12, "end": 18, "file": "bank/gameplay/race-01.mp4"}],
    })
    assert [b["start"] for b in beats] == [5.0, 12.0, 30.0]
    assert [b["section"] for b in beats] == ["zooms", "overlays", "inserts"]
    assert beats[0]["what"] == "punch ×1.2 — story"


def test_contact_sheet_marks_filler_that_owes_a_reason():
    """Артур 2026-08-01: no ceiling on how much filler a video may use — instead
    the duty to explain each one. Serial 'found nothing' is visible as laziness."""
    import chatmonteur.tools.contact_sheet as _cs

    assert _cs._is_filler(r"bank\gameplay\race-01.mp4")   # Windows path too
    assert _cs._is_filler("bank/thematic/terminal.mp4")
    assert not _cs._is_filler("projects/x/assets/tweet.png")

    beats = _cs._beats({"overlays": [
        {"start": 1, "end": 4, "file": "bank/gameplay/race-01.mp4"},
        {"start": 5, "end": 8, "file": "bank/thematic/term.mp4", "why": "связка между блоками"},
    ]})
    page = _cs._page(beats, "demo")
    assert "заливка без объяснения" in page
    assert "связка между блоками" in page
    assert page.count("class=\"owed\"") == 1


def test_contact_sheet_never_passes_off_the_footage_as_a_missing_asset():
    """Caught on the first live run: a planned asset that isn't on disk showed the
    frame UNDER it, so the reviewer would approve a beat that cannot burn."""
    import chatmonteur.tools.contact_sheet as _cs

    beats = _cs._beats({"overlays": [{"start": 4, "end": 9, "file": "bank/gameplay/nope.mp4"}]})
    assert beats[0]["missing"]

    said = []
    assert _cs._thumb(beats[0], "under.mp4", Path("x.jpg"), log=said.append) == ""
    assert any("not on disk" in m for m in said)
    assert "файла нет на диске" in _cs._page(beats, "demo")


def test_contact_sheet_quotes_the_words_the_picture_covers():
    """A picture is judged against what is being said under it, not on its own."""
    import chatmonteur.tools.contact_sheet as _cs

    segs = [{"start": 0.0, "end": 4.0, "text": " первое"},
            {"start": 4.0, "end": 9.0, "text": " второе"}]
    assert _cs._said_at(segs, 5.0) == "второе"
    assert _cs._said_at(segs, 4.0) == "второе"    # boundary belongs to the later line
    assert _cs._said_at(segs, 99.0) == ""
    assert _cs._tc(75.4) == "1:15"


def test_contact_sheet_shows_transparent_motion_over_the_real_frame(tmp_path):
    """A transparent motion snapshot on black lies about the approved result.

    The sheet must show the same composition the viewer gets: the alpha element
    over the footage, with the footage still visible outside the graphic.
    """
    from PIL import Image, ImageDraw
    import chatmonteur.tools.contact_sheet as _cs

    base = tmp_path / "base.png"
    overlay = tmp_path / "overlay.png"
    thumb = tmp_path / "thumb.jpg"
    Image.new("RGB", (320, 180), (220, 20, 20)).save(base)
    # HyperFrames components are 1920×1080 while the dogfood preview is
    # 2560×1440. Use the same 3:4 mismatch so the test catches a top-left-only
    # composite as well as a missing backplate.
    layer = Image.new("RGBA", (240, 135), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle((90, 45, 150, 90), fill=(20, 40, 220, 255))
    layer.save(overlay)

    beat = {
        "section": "motion",
        "start": 0.0,
        "file": str(overlay),
        "missing": False,
    }
    assert _cs._thumb(beat, str(base), thumb, log=lambda _msg: None).startswith("data:image/jpeg")
    rendered = Image.open(thumb).convert("RGB")
    outside = rendered.getpixel((20, 20))
    inside = rendered.getpixel((180, 90))
    assert outside[0] > 180 and outside[1] < 60 and outside[2] < 60
    assert inside[2] > 160 and inside[0] < 80


# --- bank ledger: used_in ------------------------------------------------------

def _ledger(tmp_path: Path, *rows: dict) -> Path:
    bank = tmp_path / "bank"
    (bank / "gameplay").mkdir(parents=True, exist_ok=True)
    (bank / "ledger.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return bank


def test_bank_ledger_records_which_video_used_the_asset(tmp_path):
    """Правило канала «похожие кадры не повторяются между роликами» держится
    целиком на used_in — а поле живо, только если монтаж в него пишет."""
    from chatmonteur.tools.overlays import _note_used_in

    bank = _ledger(
        tmp_path,
        {"file": "gameplay/гонка-01.mp4", "used_in": []},
        {"file": "gameplay/космос-02.mp4", "used_in": ["старый-ролик"]},
    )
    marked = _note_used_in(
        bank,
        [str(bank / "gameplay" / "гонка-01.mp4"), "projects/x/assets/tweet.png"],
        "новый-ролик",
    )

    assert marked == ["gameplay/гонка-01.mp4"]   # ассет проекта в банк не пишется
    rows = [json.loads(l) for l in (bank / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["used_in"] == ["новый-ролик"]
    assert rows[1]["used_in"] == ["старый-ролик"]   # чужие строки не трогаем


def test_bank_ledger_does_not_repeat_a_slug_on_re_render(tmp_path):
    """Перерендер — норма (превью, потом финал). Слаг должен лечь один раз,
    иначе used_in превращается в счётчик прогонов и перестаёт читаться."""
    from chatmonteur.tools.overlays import _note_used_in

    bank = _ledger(tmp_path, {"file": "gameplay/гонка-01.mp4", "used_in": ["ролик"]})
    clip = str(bank / "gameplay" / "гонка-01.mp4")

    assert _note_used_in(bank, [clip], "ролик") == []
    rows = [json.loads(l) for l in (bank / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["used_in"] == ["ролик"]


def test_bank_ledger_missing_never_breaks_a_render(tmp_path):
    """bank/ в git не уходит: у клона репозитория его нет вообще. Отсутствие
    реестра — не ошибка монтажа, рендер уже состоялся."""
    from chatmonteur.tools.overlays import _note_used_in

    said = []
    assert _note_used_in(tmp_path / "bank", ["whatever.mp4"], "ролик", log=said.append) == []
    assert not said   # нечего сказать: банка нет, ассеты не из него


def test_stock_sees_a_key_that_lives_only_in_dotenv(monkeypatch, tmp_path):
    """Ключи лежат в .env, а не в окружении процесса. Config.get_secret умеет
    читать .env — провайдер обязан спрашивать у него, иначе рабочий ключ
    невидим и tool молча говорит «нет провайдера»."""
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    (tmp_path / ".env").write_text("PEXELS_API_KEY=из-дотенва\n", encoding="utf-8")
    secret = load_config(str(tmp_path)).get_secret

    assert _stock_providers("video", None, secret) == ["pexels"]
    assert _stock_providers("video", None) == []   # без резолвера — как было


def test_pexels_picks_by_width_because_that_is_what_gets_scaled():
    """Оверлей масштабируется по ШИРИНЕ кадра (scale=target_w:-2), фон — тоже.
    Критерий по высоте врёт на вертикальных кандидатах: живая выкачка принесла
    720x1280 как «достаточное 1080p», а по ширине это 720."""
    from chatmonteur.tools.stock import _pexels_file

    files = [{"width": 640, "height": 360, "link": "a"},
             {"width": 3840, "height": 2160, "link": "b"},
             {"width": 1920, "height": 1080, "link": "c"},
             {"width": 720, "height": 1280, "link": "вертикаль"}]
    assert _pexels_file(files, 1280) == "c"      # самый лёгкий, которого ХВАТАЕТ по ширине
    assert _pexels_file(files, 2560) == "b"      # ниже цели нет — берём максимум
    assert _pexels_file([{"width": 640, "height": 360, "link": "e"}], 1280) == "e"
    assert _pexels_file([], 1280) is None


def test_sfx_kind_routes_to_freesound_only_with_a_key(monkeypatch, tmp_path):
    """SFX — четвёртый вид материала рядом с image/video/meme, а не отдельный
    инструмент: качает кандидатов, ведёт manifest, тот же селектор провайдеров."""
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    assert _stock_providers("sfx", None) == []
    (tmp_path / ".env").write_text("FREESOUND_API_KEY=токен\n", encoding="utf-8")
    assert _stock_providers("sfx", None, load_config(str(tmp_path)).get_secret) == ["freesound"]


def test_freesound_licence_flags_come_from_the_licence_url():
    """Freesound отдаёт лицензию ссылкой. CC0 не требует ничего; by — строку в
    описании ролика; by-nc и sampling+ ограничивают коммерческое использование —
    канал не монетизируется, но пометка нужна, чтобы потом было что перебрать."""
    from chatmonteur.tools.stock import _licence_flags

    assert _licence_flags("http://creativecommons.org/publicdomain/zero/1.0/") == (False, False)
    assert _licence_flags("https://creativecommons.org/licenses/by/4.0/") == (True, False)
    assert _licence_flags("https://creativecommons.org/licenses/by-nc/4.0/") == (True, True)
    assert _licence_flags("https://creativecommons.org/licenses/sampling+/1.0/") == (True, True)
