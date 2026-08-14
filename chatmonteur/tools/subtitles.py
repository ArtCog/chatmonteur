"""Capability: ``subtitles`` — build captions from a transcript and burn them in.

Takes a transcript JSON (from ``transcribe``), segments it into readable cues, and
burns captions onto the video. Re-encodes (never stream-copies).

Five brand «Mono» styles (see ``assets/brand/default/brand.md`` and
``skills/subtitles.md``) — the DRIVING AGENT picks one per video, this tool draws it:

* ``clean``       — C · чисто: plain line, no per-word motion. The pipeline default.
* ``read_aloud``  — A · читаем вслух: words fade in one-by-one, synced to speech.
* ``accent``      — B · акцент: the marked word (``"emph": true``) inverted into a chip.
* ``typewriter``  — D · печатная машинка: JetBrains Mono, typed char-by-char + cursor.
* ``highlight``   — E · караоке: whole line visible; the word being SPOKEN inverts
                    into the chip in sync (the dominant 2026 caption look).

Card 04 as drawn (Артур 2026-08-03, supersedes the 2026-07-24 "no plate" call):
the line sits on a scrim and a key word is accented by INVERSION, never by colour.
Geometry is fixed (5.5% / 9% / 80%); motion and font differ by variant.
"""

from __future__ import annotations

import json

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import brand as brandkit, media


class SubtitlesTool(Tool):
    manifest = ToolManifest(
        name="subtitles_ffmpeg",
        capability="subtitles",
        summary="Build captions from transcript and burn them with ffmpeg (4 brand styles).",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        transcript: str,
        max_chars: int = 39,  # Cyrillic-friendly CPL (≤39); safe for latin too
        burn: bool = True,
        variant: str = "clean",
        font: str | None = None,
        font_dir: str | None = None,
    ) -> ToolResult:
        media.require("ffmpeg")
        if variant not in _VARIANTS:
            raise ToolError(f"unknown subtitle variant {variant!r}; choose one of {sorted(_VARIANTS)}")
        style = _brand_style(ctx.config.brand.name, variant)
        font = font or style["font"]
        font_dir = font_dir or style["font_dir"]
        data = json.loads(open(transcript, encoding="utf-8").read())
        srt_path = ctx.paths.transcripts / "captions.srt"
        srt_path.write_text(_to_srt(data, max_chars), encoding="utf-8")

        cues = sum(1 for s in data.get("segments", []) if s.get("text", "").strip())
        artifacts = {"srt": str(srt_path)}
        if not burn:
            # Default on this channel: captions stay OFF (meaning-inserts are the text
            # layer). The SRT is still written — YouTube takes it as a caption file.
            ctx.log("subtitles: burn off — SRT only, video passes through")
            artifacts["video"] = str(input)
        elif burn and not cues:
            # Nothing to burn (e.g. silent/music clip) — pass the video through.
            ctx.log("subtitles: empty transcript, skipping burn")
            artifacts["video"] = str(input)
        elif burn:
            encoder = media.detect_encoder(ctx.config.encode.encoder)
            out = ctx.paths.clips / "subtitled.mp4"
            w, h = _video_wh(input)
            # ASS (not SRT+force_style): its header pins PlayResX/Y to the real
            # frame, so FontSize/margins are REAL PIXELS. SRT+force_style is scaled
            # by libass's default 288 PlayResY → a giant caption. (Learned the hard way.)
            ass_path = ctx.paths.transcripts / "captions.ass"
            ass_path.write_text(
                _to_ass(data, max_chars, w, h, font, variant, palette=style),
                encoding="utf-8",
            )
            artifacts["ass"] = str(ass_path)
            fd = f":fontsdir='{media.filter_path(font_dir)}'" if font_dir else ""
            # Run from the ASS's folder, reference by bare name (dodge drive colon).
            media.run(
                [
                    "ffmpeg", "-y", "-i", str(input),
                    "-vf", f"ass={ass_path.name}{fd},format=yuv420p",
                    "-c:v", encoder, *media.encoder_quality_args(encoder),
                    "-pix_fmt", "yuv420p",
                    "-c:a", "copy",
                    str(out),
                ],
                log=ctx.log,
                desc=f"burn subtitles ({variant}, {font}, {h}p)",
                cwd=ass_path.parent,
            )
            artifacts["video"] = str(out)
        return ToolResult(
            artifacts=artifacts,
            meta={"variant": variant, "cues": data and len(data.get("segments", [])),
                  "brand": ctx.config.brand.name},
        )


# --- THE STANDARD --------------------------------------------------------------
# GEOMETRY (agreed in the tuner): size/position as a fraction of frame height so
# they hold at any resolution. STYLE (font/colour/plate): from the brand kit
# «ИИмерсивный - Mono» — Golos Text Bold, paper-white on a semi-transparent scrim
# (design "C · чисто" — the default caption). Mirrors skills/subtitles.md +
# Runtime rendering resolves the active pack. Constants below preserve the
# bundled default for direct helper calls and backwards-compatible tests.
_SIZE_FRAC = 0.055    # font size = 5.5% of frame height (Артур 2026-07-24: «чуть увеличить»)
_MARGIN_FRAC = 0.09   # bottom margin = 9% of frame height (above player controls)
_WIDTH_FRAC = 0.80    # text area = 80% of frame width (L+R margins take the rest)
_FADE_MS = 150        # per-word soft-in for read_aloud (brand: ~0.2s)

# Brand colours as ASS BGR (&HAABBGGRR; AA alpha: 00 opaque … FF transparent).
_PAPER_BGR = "&H00F7FAFA"    # paper #FAFAF7 — caption text
_PAPER_C = "&HF7FAFA&"       # paper as a \1c value (flip back after a highlight)
_INK_C = "&H0D0B0B&"         # ink #0B0B0D — text inside an inverted chip
# Scrim behind the line: ink #08090A at 52% opacity, exactly card 04's
# rgba(8,9,10,.52). Alpha 0x7A = (1 − 0.52) × 255.
_SCRIM_BGR = "&H7A0A0908"    # style-line form (&HAABBGGRR)
_SCRIM_C = "&H0A0908&"       # the same colour as an inline \3c value
_VARIANTS = {"clean", "read_aloud", "accent", "typewriter", "highlight"}
# Plate rule (Артур 2026-08-03, FINAL — supersedes the 2026-07-24 "no plate"):
# captions follow card 04 as drawn. The line sits on a scrim, and a key word is
# accented by INVERSION (paper chip, ink text), not by colour — the brandbook's
# own rule is that colour never carries text. Caption yellow #FFD700 is retired
# here alongside the green that went with the monochrome refresh.
#
# Both boxes are ASS BorderStyle 3 ("opaque box"), whose fill is OutlineColour and
# whose padding is Outline — so a chip is an inline \3c + \3a + \bord on the word.
# Verified by rendering: libass DOES box a span inside a scrimmed line (an earlier
# note in the plan claimed otherwise). The one thing it cannot do is asymmetric
# padding — the designer's 7/16 px scrim and 3/11 px chip become one value each,
# matched to the VERTICAL number because the band's thickness is what reads.
_TYPE_SCALE = 23 / 26
_SCRIM_PAD_EM = 7 / 26       # card 04: 7px padding at a 26px face
_CHIP_PAD_EM = 3 / 26        # card 04: the chip nests inside the scrim
_SHADOW_EM = 0.05            # shadow offset as a fraction of font size
_SHADOW_BGR = "&H800A0908"   # ink #08090A at ~50% — the drop shadow colour
def _brand_style(name: str = "default", variant: str = "clean") -> dict[str, str]:
    """Resolve the active pack into the ASS values used by the subtitle renderer."""
    brandkit.validate_runtime(name)
    _, _, _, scrim_opacity = brandkit.rgba("scrim", brand=name)
    scrim_alpha = round((1.0 - scrim_opacity) * 255)
    return {
        "font": brandkit.font("mono" if variant == "typewriter" else "sans", brand=name),
        "font_dir": str(brandkit.font_dir(name)),
        "paper_bgr": brandkit.ass_style("paper", brand=name, alpha=0),
        "paper_c": brandkit.ass_override("paper", brand=name),
        "ink_c": brandkit.ass_override("ink", brand=name),
        "scrim_bgr": brandkit.ass_style("scrim", brand=name),
        "scrim_c": brandkit.ass_override("scrim", brand=name),
        "scrim_alpha": f"&H{scrim_alpha:02X}&",
        "shadow_bgr": brandkit.ass_style("ink", brand=name, alpha=128),
    }


def _palette(values: dict[str, str] | None) -> dict[str, str]:
    return values or {
        "paper_bgr": _PAPER_BGR, "paper_c": _PAPER_C, "ink_c": _INK_C,
        "scrim_bgr": _SCRIM_BGR, "scrim_c": _SCRIM_C,
        "scrim_alpha": "&H7A&", "shadow_bgr": _SHADOW_BGR,
    }


def _video_wh(path: str) -> tuple[int, int]:
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            return int(s.get("width", 1920)), int(s["height"])
    return 1920, 1080


# --- ASS document --------------------------------------------------------------

def _to_ass(data: dict, max_chars: int, width: int, height: int, font: str, variant: str,
            palette: dict[str, str] | None = None) -> str:
    """ASS with PlayRes pinned to the real frame → FontSize/margins are real px.

    One Dialogue per cue; the per-variant renderer decides how the cue's text
    animates. No plate, no outline — bold text with a soft drop shadow only.
    """
    fs = round(_SIZE_FRAC * height)
    if variant == "typewriter":
        fs = round(fs * _TYPE_SCALE)             # designer: D is 23px at A-C's 26
    mv = round(_MARGIN_FRAC * height)
    side = round((1 - _WIDTH_FRAC) / 2 * width)  # L/R margin → 80% text width
    bold = 0 if variant == "typewriter" else -1  # D is Mono 500, others Golos 700
    sh = max(2, round(_SHADOW_EM * fs))          # soft drop shadow under the scrim
    scrim = max(2, round(_SCRIM_PAD_EM * fs))    # box padding = the scrim's thickness
    colours = _palette(palette)
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        f"PlayResX: {width}\nPlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # BorderStyle 3 → opaque box: OutlineColour fills it, Outline is its padding.
        f"Style: Default,{font},{fs},{colours['paper_bgr']},{colours['paper_bgr']},"
        f"{colours['scrim_bgr']},{colours['shadow_bgr']},"
        f"{bold},0,0,0,100,100,0,0,3,{scrim},{sh},2,{side},{side},{mv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    render = _RENDERERS[variant]
    lines = []
    for cue in _build_cues(data, max_chars):
        body = render(cue, max_chars, fs, colours)
        lines.append(
            f"Dialogue: 0,{_ass_time(cue['start'])},{_ass_time(cue['end'])},Default,,0,0,0,,{body}"
        )
    return header + "\n".join(lines) + "\n"


# --- per-variant cue renderers (cue -> ASS body text) --------------------------

def _r_clean(cue: dict, max_chars: int, fs: int = 0,
             palette: dict[str, str] | None = None) -> str:
    """C · чисто — the whole line at once, brand soft-in fade."""
    return "{\\fad(180,0)}" + _wrap(cue["text"], max_chars).replace("\n", "\\N")


def _r_read_aloud(cue: dict, max_chars: int, fs: int = 0,
                  palette: dict[str, str] | None = None) -> str:
    """A · читаем вслух — each word fades in at its own spoken time."""
    words = cue.get("words") or []
    if not words:
        return _r_clean(cue, max_chars)  # no timings → can't stagger, show as clean
    base = cue["start"]
    tokens = [{"text": w["word"].strip(), "start": float(w["start"])}
              for w in words if w["word"].strip()]

    def render(tok: dict) -> str:
        t1 = max(0, int((tok["start"] - base) * 1000))
        return f"{{\\alpha&HFF&\\t({t1},{t1 + _FADE_MS},\\alpha&H00&)}}{tok['text']}"

    return _layout(tokens, max_chars, render)


def _scrim_pad(fs: int) -> int:
    return max(2, round(_SCRIM_PAD_EM * fs))


def _chip_state(fs: int, palette: dict[str, str] | None = None) -> str:
    """Override that turns a span into the inverted chip: paper box, ink text.

    \\3a is set explicitly — inheriting the scrim's 52% alpha tints the chip grey
    instead of paper, which is exactly how the first test render came out.
    """
    colours = _palette(palette)
    return (f"\\3c{colours['paper_c']}\\3a&H00&"
            f"\\bord{max(2, round(_CHIP_PAD_EM * fs))}\\1c{colours['ink_c']}")


def _scrim_state(fs: int, palette: dict[str, str] | None = None) -> str:
    """Override that returns a span to the ordinary scrimmed line.

    Not \\bord0: the box IS the scrim, so a word with no border punches a notch
    out of the band instead of blending back into it.
    """
    colours = _palette(palette)
    return (f"\\3c{colours['scrim_c']}\\3a{colours['scrim_alpha']}"
            f"\\bord{_scrim_pad(fs)}\\1c{colours['paper_c']}")


def _chip(text: str, fs: int, palette: dict[str, str] | None = None) -> str:
    """Wrap one word in the inverted chip (card 04, style B)."""
    return f"{{{_chip_state(fs, palette)}}}{text}{{\\r}}"


def _r_accent(cue: dict, max_chars: int, fs: int = 0,
              palette: dict[str, str] | None = None) -> str:
    """B · акцент — the emphasised word (``"emph": true``) inverted into a chip.

    Card 04 accents by inversion, and the brandbook's rule is that colour never
    carries text — so the key word flips to ink-on-paper rather than changing hue.
    """
    words = cue.get("words") or []
    if not words:
        return _r_clean(cue, max_chars)
    tokens = [{"text": w["word"].strip(), "emph": bool(w.get("emph"))}
              for w in words if w["word"].strip()]
    if not any(t["emph"] for t in tokens):
        return _r_clean(cue, max_chars)  # nothing marked → plain line

    def render(tok: dict) -> str:
        return _chip(tok["text"], fs, palette) if tok["emph"] else tok["text"]

    return "{\\fad(180,0)}" + _layout(tokens, max_chars, render)


def _r_highlight(cue: dict, max_chars: int, fs: int = 0,
                 palette: dict[str, str] | None = None) -> str:
    """E · караоке — the whole line shows at once; the word being SPOKEN inverts
    into a chip, then flips back. Needs word timings.

    The chip appears and leaves instantly (\\t over 0ms): a box that fades reads as
    a rendering fault, where a hard flip reads as a beat landing on the word.
    """
    words = cue.get("words") or []
    if not words:
        return _r_clean(cue, max_chars)
    base = cue["start"]
    tokens = [{"text": w["word"].strip(),
               "s": max(0, int((float(w["start"]) - base) * 1000)),
               "e": max(0, int((float(w["end"]) - base) * 1000))}
              for w in words if w["word"].strip()]

    def render(tok: dict) -> str:
        s, e = tok["s"], max(tok["e"], tok["s"] + 120)  # holds ≥120ms, never blinks
        return (f"{{\\t({s},{s},{_chip_state(fs, palette)})"
                f"\\t({e},{e},{_scrim_state(fs, palette)})}}"
                f"{tok['text']}{{\\r}}")

    return "{\\fad(180,0)}" + _layout(tokens, max_chars, render)


def _r_typewriter(cue: dict, max_chars: int, fs: int = 0,
                  palette: dict[str, str] | None = None) -> str:
    """D · печатная машинка — chars type in at a steady pace, cursor follows the caret.

    Untyped chars are hidden AND zero-width (`\\fscx0`), not just transparent — else the
    line reserves their width and the cursor floats at the line end instead of the caret.
    Steady linear pace over ~85% of the cue (a real typewriter is even, not speech-synced).
    """
    text = _wrap(cue["text"], max_chars)
    dur = cue["end"] - cue["start"]
    per = dur * 0.85 / max(1, len(text))  # seconds per character
    out = []
    for i, ch in enumerate(text):
        if ch == "\n":
            out.append("\\N")  # newline is already zero-width
            continue
        ms = int(per * 1000 * i)
        out.append(f"{{\\fscx0\\alpha&HFF&\\t({ms},{ms + 1},\\fscx100\\alpha&H00&)}}{ch}")
    out.append("\\h" + _blink_cursor(cue))  # trailing ▌ blinking at ~1 Hz, sits at the caret
    return "".join(out)


def _blink_cursor(cue: dict, period_ms: int = 500) -> str:
    """A ▌ that toggles visibility every ``period_ms`` across the cue (terminal blink)."""
    dur = int((cue["end"] - cue["start"]) * 1000)
    toggles = ["\\alpha&H00&"]  # start visible
    k = 1
    while period_ms * k < dur:
        t = period_ms * k
        toggles.append(f"\\t({t},{t + 1},\\alpha&H{'FF' if k % 2 else '00'}&)")
        k += 1
    return "{" + "".join(toggles) + "}▌"


_RENDERERS = {
    "clean": _r_clean,
    "read_aloud": _r_read_aloud,
    "accent": _r_accent,
    "typewriter": _r_typewriter,
    "highlight": _r_highlight,
}


# Short function words that must never END a caption line — BBC: keep a preposition
# with its noun, a conjunction with its clause. Carried down to the next line.
_ORPHANS = {
    "в", "во", "с", "со", "к", "ко", "у", "о", "об", "обо", "из", "изо", "по", "на",
    "за", "над", "под", "до", "от", "ото", "не", "ни", "и", "а", "но", "да", "же",
    "бы", "ли", "что", "как", "для", "при", "про", "без", "через",
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or",
}


def _is_orphan(word: str) -> bool:
    return word.strip(".,!?;:—…\"'»«()").lower() in _ORPHANS


def _break_lines(words: list[str], max_chars: int) -> list[list[int]]:
    """Greedy wrap to ≤``max_chars``-char lines, returning word INDICES per line.

    Then an orphan pass: no line but the last may end on a short function word —
    it is carried down to stay with its noun (may slightly overflow, worth it).
    """
    lines: list[list[int]] = []
    cur: list[int] = []
    cur_len = 0
    for i, w in enumerate(words):
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > max_chars:
            lines.append(cur)
            cur, cur_len, add = [], 0, len(w)
        cur.append(i)
        cur_len += add
    if cur:
        lines.append(cur)
    for li in range(len(lines) - 1):
        while len(lines[li]) > 1 and _is_orphan(words[lines[li][-1]]):
            lines[li + 1].insert(0, lines[li].pop())
    return lines


def _layout(tokens: list[dict], max_chars: int, render) -> str:
    """Lay word-tokens into lines (\\N between), each rendered via ``render``, tags intact.

    Width is measured on the plain word text, not the tagged ASS string.
    """
    words = [t["text"] for t in tokens]
    lines = _break_lines(words, max_chars)
    return "\\N".join(" ".join(render(tokens[i]) for i in ln) for ln in lines)


# --- timing / text helpers -----------------------------------------------------

def _ass_time(t: float) -> str:
    # Quantise BEFORE splitting into fields: 59.997 formatted per-field yields
    # the invalid "0:00:60.00" — the carry must reach the minutes.
    cs = round(max(t, 0.0) * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _fmt(t: float) -> str:
    ms = round(max(t, 0.0) * 1000)
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap(text: str, max_chars: int) -> str:
    words = text.split()
    lines = _break_lines(words, max_chars)
    return "\n".join(" ".join(words[i] for i in ln) for ln in lines)


# --- cue segmentation ----------------------------------------------------------

def _chunk_words(words: list[dict], max_chars: int, max_dur: float = 2.8, max_lines: int = 2):
    """Group word-timestamps into short caption cues (talking-head style).

    Breaks on sentence punctuation, ~max_chars*max_lines length, max_dur — or on a
    PAUSE in the speech. The pause rule is what makes captions breathe with the
    voice instead of snapping at an arbitrary word count: where the speaker took a
    breath, the line changes. A pause only ends a cue that has already earned its
    minimum time on screen, so this splits phrases without shredding them.

    Each cue keeps its own words (needed by the read_aloud / accent / typewriter
    renderers).
    """
    cues, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text = "".join(x.get("word", "") for x in cur).strip()
        dur = float(cur[-1]["end"]) - float(cur[0]["start"])
        gap = float(words[i + 1]["start"]) - float(w["end"]) if i + 1 < len(words) else 0.0
        if (len(text) >= max_chars * max_lines or dur >= max_dur
                or text.endswith((".", "!", "?", "…"))
                or (gap >= _PAUSE_BREAK and dur >= _MIN_DUR)):
            cues.append((float(cur[0]["start"]), float(cur[-1]["end"]), text, list(cur)))
            cur = []
    if cur:
        text = "".join(x.get("word", "") for x in cur).strip()
        cues.append((float(cur[0]["start"]), float(cur[-1]["end"]), text, list(cur)))
    return cues


def _build_cues(data: dict, max_chars: int) -> list[dict]:
    """Segment a transcript into short caption cues (shared by SRT + ASS).

    Each cue: ``{start, end, text, words}`` — ``words`` is the list of word dicts in
    that cue (empty when the segment carried no word timings).
    """
    cues: list[dict] = []
    for seg in data.get("segments", []):
        words = seg.get("words")
        if words:
            for start, end, text, ws in _chunk_words(words, max_chars):
                cues.append({"start": start, "end": end, "text": text, "words": ws})
        elif seg.get("text", "").strip():
            cues.append({
                "start": float(seg["start"]), "end": float(seg["end"]),
                "text": seg["text"].strip(), "words": [],
            })
    return _fit_timing(_merge_flashes(cues, max_chars))


def _merge_flashes(cues: list[dict], max_chars: int) -> list[dict]:
    """Merge cues too short to display into the PREVIOUS cue.

    _fit_timing can only extend into free time; when the next cue starts
    immediately (dense speech) a short cue would flash regardless. Such a cue
    is usually the tail of the previous sentence — merging backward keeps it
    with its sentence. Skipped when the merged text would exceed 2 lines.
    """
    out: list[dict] = []
    for c in cues:
        prev = out[-1] if out else None
        if (prev is not None and c["end"] - c["start"] < _MIN_DUR
                and len(prev["text"]) + 1 + len(c["text"]) <= max_chars * 2):
            prev["end"] = c["end"]
            prev["text"] += " " + c["text"]
            if prev["words"] and c["words"]:
                prev["words"] += c["words"]
            else:
                # Half-timed words make a karaoke cue DISPLAY only the timed half.
                # No timings at all falls back to the clean render — text intact.
                prev["words"] = []
        else:
            out.append(c)
    return out


# Reading-comfort limits (Netflix/BBC). See skills/subtitles.md.
_MIN_DUR = 0.83   # a cue must hold ≥0.83 s — never flash
_PAUSE_BREAK = 0.15  # a gap this long is a breath: end the cue there, not mid-phrase
_MAX_DUR = 7.0    # …and not linger past ~7 s
_MAX_CPS = 17.0   # ≤17 characters/second reading speed
_GAP = 0.08       # keep ≥~2 frames between cues when extending


def _fit_timing(cues: list[dict]) -> list[dict]:
    """Extend cues that flash or read too fast — into free time only, never overlapping.

    Only lengthens (holds a caption longer); never shortens and never cuts words.
    Best-effort: if the next cue is right behind, the caption keeps what room there is.
    """
    for i, c in enumerate(cues):
        need = max(_MIN_DUR, len(c["text"]) / _MAX_CPS)  # min-duration AND CPS in one
        end = max(c["end"], c["start"] + need)
        end = min(end, c["start"] + _MAX_DUR)
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
        if nxt is not None:
            end = min(end, max(c["end"], nxt - _GAP))  # don't push into next; don't shorten
        c["end"] = end
    return cues


def _to_srt(data: dict, max_chars: int) -> str:
    out = []
    for i, cue in enumerate(_build_cues(data, max_chars), start=1):
        wrapped = _wrap(cue["text"], max_chars)
        if wrapped:
            out.append(f"{i}\n{_fmt(cue['start'])} --> {_fmt(cue['end'])}\n{wrapped}\n")
    return "\n".join(out)


TOOL = SubtitlesTool()
