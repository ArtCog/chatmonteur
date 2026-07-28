"""Capability: ``inserts`` — burn meaning-inserts (смысловые текстовые вставки).

NOT subtitles. Selective pop-up text at key beats only: an attention emoji above a
single line that states the POINT of what is being said, with the key words in the
accent colour (the MrBeast/Ривера pattern — see ``skills/motion.md``).

The DECISION is the AGENT's job, as always (D11): reading the final-cut transcript,
choosing the beats, condensing the thought into one short line, picking the emoji and
the key words, and getting them approved. This tool is the "hands" — it draws the
approved cards and burns them in one ffmpeg pass.

Insert plan (JSON, authored by the agent)::

    {"inserts": [
      {"start": 5.5, "end": 8.8, "emoji": "🚫",
       "text": "ноль программ монтажа", "key": "ноль программ"}
    ]}

``key`` is optional (a substring of ``text`` to accent); ``emoji`` is optional too.
Rendered via ASS — the same engine as subtitles, no extra dependency.
"""

from __future__ import annotations

import json
import pathlib
import sys

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media


class InsertsTool(Tool):
    manifest = ToolManifest(
        name="inserts_ffmpeg",
        capability="inserts",
        summary="Burn agent-authored meaning-inserts (emoji + one-line point) with ffmpeg.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        inserts: str,
        style: str = "emoji_top",
        accent: str = "yellow",
        font: str | None = None,
        font_dir: str | None = None,
        emoji_font: str | None = None,
    ) -> ToolResult:
        media.require("ffmpeg")
        if style not in _STYLES:
            raise ToolError(f"unknown insert style {style!r}; choose one of {sorted(_STYLES)}")
        if accent not in _ACCENTS:
            raise ToolError(f"unknown accent {accent!r}; choose one of {sorted(_ACCENTS)}")
        plan_path = pathlib.Path(inserts)
        if not plan_path.is_file():
            raise ToolError(
                f"insert plan not found: {plan_path} (the agent writes it after storyboard approval)"
            )
        items = _load_plan(plan_path)
        if not items:
            ctx.log("inserts: plan is empty, passing the video through")
            return ToolResult(artifacts={"video": str(input)}, meta={"inserts": 0})

        font = font or _BRAND_FONT
        font_dir = font_dir or _BRAND_FONT_DIR
        emoji_font = emoji_font or _default_emoji_font()
        w, h = _video_wh(input)
        ass_path = ctx.paths.transcripts / "inserts.ass"
        ass_path.write_text(_to_ass(items, w, h, font, style, accent), encoding="utf-8")

        encoder = media.detect_encoder(ctx.config.encode.encoder)
        out = ctx.paths.clips / "inserted.mp4"
        fd = f":fontsdir='{media.filter_path(font_dir)}'" if font_dir else ""
        # Emoji are drawn as PNGs and overlaid: libass renders only OUTLINE glyphs, so a
        # colour emoji font (COLR/CBDT) comes out grey through `ass=` — verified on a real
        # frame. Text stays in ASS; only the emoji becomes a picture.
        emoji_pngs = _render_emoji(items, es=round(_EMOJI_FRAC * h),
                                   out_dir=ctx.paths.clips, log=ctx.log)
        cmd = ["ffmpeg", "-y", "-i", str(input)]
        for it in emoji_pngs:
            cmd += ["-loop", "1", "-t", f"{it['end'] - it['start']:.3f}", "-i", it["png"]]
        cmd += ["-filter_complex", _filter_graph(ass_path.name, fd, emoji_pngs, h),
                "-map", "[v]", "-map", "0:a?"]
        cmd += ["-c:v", encoder, *media.encoder_quality_args(encoder),
                "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
        media.run(
            cmd,
            log=ctx.log,
            desc=f"burn {len(items)} inserts ({style}/{accent}, {h}p)",
            cwd=ass_path.parent,
        )
        return ToolResult(
            artifacts={"video": str(out), "ass": str(ass_path)},
            meta={"inserts": len(items), "style": style, "accent": accent,
                  "emoji_drawn": len(emoji_pngs)},
        )


# --- THE STANDARD (Артур 2026-07-26) -------------------------------------------
# «Эмоджи сверху» is the locked default: attention emoji above ONE short line, bold
# white, key words in juicy yellow, no plate — just a soft shadow. Sizes are
# fractions of frame height so they hold at 1080p and 1440p. Mirrors skills/motion.md.
_EMOJI_FRAC = 0.125    # emoji size = 12.5% of frame height (135px @1080)
_TEXT_FRAC = 0.089     # text size  = 8.9% of frame height (96px @1080)
_BOTTOM_FRAC = 0.11    # text sits 11% of frame height above the bottom edge
_GAP_FRAC = 0.012      # gap between the text block and the emoji
_MAX_CHARS = 28        # inserts are BIG: keep lines short, wrap beyond this

_PAPER = "&H00F7FAFA"      # paper #FAFAF7 — the text
_INK = "&H000C0B0B"        # ink #0B0B0C — text on the sticker plate
_SHADOW = "&H800A0908"     # ink @50% — soft drop shadow, never an outline
_SHADOW_EM = 0.05
# Accent per surface: a key word must stay legible both on footage and on paper.
_ACCENTS = {
    "yellow": {"dark": "&H00D7FF&", "paper": "&H0C59E8&"},   # #FFD700 / #E8590C
    "green": {"dark": "&H6AE82B&", "paper": "&H4B8617&"},    # #2BE86A / #17864B
}
_STYLES = {"emoji_top", "sticker"}
_BRAND_FONT = "Golos Text"
_BRAND_FONT_DIR = str(
    pathlib.Path(__file__).resolve().parents[2] / "assets" / "brand" / "default" / "fonts"
)
_EMOJI_FONTS = {
    "win32": "Segoe UI Emoji",
    "darwin": "Apple Color Emoji",
}


def _default_emoji_font() -> str:
    return _EMOJI_FONTS.get(sys.platform, "Noto Color Emoji")


def _load_plan(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("inserts", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ToolError("insert plan must be a list (or {'inserts': [...]})")
    out = []
    for i, it in enumerate(items):
        text = str(it.get("text", "")).strip()
        if not text:
            raise ToolError(f"insert #{i + 1} has no text")
        start, end = float(it["start"]), float(it["end"])
        if end <= start:
            raise ToolError(f"insert #{i + 1}: end ({end}) must be after start ({start})")
        out.append({
            "start": start, "end": end, "text": text,
            "emoji": str(it.get("emoji", "")).strip(),
            "key": str(it.get("key", "")).strip(),
        })
    return out


def _video_wh(path: str) -> tuple[int, int]:
    for s in media.ffprobe_json(path).get("streams", []):
        if s.get("codec_type") == "video" and s.get("height"):
            return int(s.get("width", 1920)), int(s["height"])
    return 1920, 1080


# --- ASS document --------------------------------------------------------------

def _to_ass(items: list[dict], width: int, height: int, font: str,
            style: str, accent: str) -> str:
    """One event per insert — the text line. The emoji is overlaid as a PNG."""
    ts = round(_TEXT_FRAC * height)
    sh = max(2, round(_SHADOW_EM * ts))
    bottom = round(_BOTTOM_FRAC * height)
    side = round(0.06 * width)
    sticker = style == "sticker"
    ac = _ACCENTS[accent]["paper" if sticker else "dark"]
    # Sticker = paper plate (BorderStyle 3) with ink text; standard = shadow only.
    text_style = (
        f"Style: Ins,{font},{ts},{_INK},{_INK},{_PAPER},{_PAPER},-1,0,0,0,100,100,0,0,"
        f"3,{round(ts * 0.34)},0,2,{side},{side},{bottom},1"
        if sticker else
        f"Style: Ins,{font},{ts},{_PAPER},{_PAPER},{_SHADOW},{_SHADOW},-1,0,0,0,100,100,0,0,"
        f"1,0,{sh},2,{side},{side},{bottom},1"
    )
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
        f"{text_style}\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for it in items:
        t0, t1 = _ass_time(it["start"]), _ass_time(it["end"])
        body = _wrap(_escape(it["text"]), _MAX_CHARS).replace("\n", "\\N")
        body = _accent_key(body, it["key"], ac)
        lines.append(f"Dialogue: 0,{t0},{t1},Ins,,0,0,0,,{_POP}{body}")
    return header + "\n".join(lines) + "\n"


# Soft pop-in: scale from 92% and fade, per the brand's «soft-in» easing feel.
_POP = "{\\fad(180,220)\\fscx92\\fscy92\\t(0,150,\\fscx100\\fscy100)}"


# --- emoji as pictures ---------------------------------------------------------

def _emoji_bottom(height: int, lines: int = 1) -> int:
    """Distance from the frame bottom to the BOTTOM of the emoji.

    Clears the WHOLE text block — a two-line insert is twice as tall, and an emoji
    positioned for one line lands on the first line's words (dogfood v2 find).
    """
    ts = round(_TEXT_FRAC * height)
    return round(_BOTTOM_FRAC * height) + round(ts * 1.15 * max(1, lines)) + round(_GAP_FRAC * height)


def _render_emoji(items: list[dict], es: int, out_dir: pathlib.Path, log) -> list[dict]:
    """Draw each insert's emoji to a transparent PNG. Skips silently without Pillow.

    Colour emoji fonts are COLR/CPAL (vector layers) or CBDT/sbix (embedded bitmaps);
    Pillow draws both with ``embedded_color=True``. Bitmap fonts only hold fixed sizes,
    so on failure we render at the native 109 px and scale up.
    """
    wanted = [it for it in items if it["emoji"]]
    for it in wanted:
        it["lines"] = len(_wrap(it["text"], _MAX_CHARS).split("\n"))
    if not wanted:
        return []
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log("inserts: Pillow not installed — drawing inserts without emoji "
            "(pip install pillow to enable them)")
        return []
    path = _emoji_font_file()
    if not path:
        log("inserts: no colour emoji font found on this system — inserts drawn without emoji")
        return []

    out = []
    for i, it in enumerate(wanted):
        try:
            png = out_dir / f"emoji_{i + 1}.png"
            img = _draw_emoji(it["emoji"], es, path, Image, ImageDraw, ImageFont)
            img.save(png)
            out.append({"png": str(png), "start": it["start"], "end": it["end"],
                        "lines": it.get("lines", 1)})
        except Exception as exc:  # noqa: BLE001 — a bad glyph must not kill the render
            log(f"inserts: could not draw emoji {it['emoji']!r} ({exc}); that insert goes text-only")
    return out


def _draw_emoji(char: str, size: int, font_path: str, Image, ImageDraw, ImageFont):
    """Render one emoji glyph, trimmed to its ink, at ``size`` px tall."""
    try:
        font = ImageFont.truetype(font_path, size)
        native = size
    except OSError:
        font = ImageFont.truetype(font_path, _BITMAP_EM)  # CBDT: fixed strike only
        native = _BITMAP_EM
    canvas = Image.new("RGBA", (native * 2, native * 2), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((native // 2, native // 2), char, font=font,
                                embedded_color=True, fill=(255, 255, 255, 255))
    canvas = canvas.crop(canvas.getbbox() or (0, 0, native, native))
    if canvas.height != size:
        w = max(1, round(canvas.width * size / canvas.height))
        canvas = canvas.resize((w, size), Image.LANCZOS)
    return canvas


_BITMAP_EM = 109  # Noto Color Emoji's built-in bitmap strike
_EMOJI_FILES = {
    "win32": ["C:/Windows/Fonts/seguiemj.ttf"],
    "darwin": ["/System/Library/Fonts/Apple Color Emoji.ttc"],
}
_EMOJI_FILES_LINUX = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
]


def _emoji_font_file() -> str | None:
    for p in _EMOJI_FILES.get(sys.platform, _EMOJI_FILES_LINUX):
        if pathlib.Path(p).is_file():
            return p
    return None


def _filter_graph(ass_name: str, fontsdir: str, emoji: list[dict], height: int) -> str:
    """ASS text first, then each emoji PNG overlaid for its own window, alpha-faded."""
    parts = [f"[0:v]ass={ass_name}{fontsdir}[v0]"]
    for i, e in enumerate(emoji):
        dur = e["end"] - e["start"]
        bottom = _emoji_bottom(height, e.get("lines", 1))  # per-insert: clear ALL its lines
        parts.append(
            f"[{i + 1}:v]format=rgba,fade=in:st=0:d=0.18:alpha=1,"
            f"fade=out:st={max(0.0, dur - 0.22):.3f}:d=0.22:alpha=1,"
            f"setpts=PTS+{e['start']:.3f}/TB[e{i}]"
        )
        parts.append(
            f"[v{i}][e{i}]overlay=(W-w)/2:H-h-{bottom}:"
            f"enable='between(t,{e['start']:.3f},{e['end']:.3f})'[v{i + 1}]"
        )
    parts.append(f"[v{len(emoji)}]format=yuv420p[v]")
    return ";".join(parts)


def _accent_key(body: str, key: str, colour: str) -> str:
    """Colour the key substring (case-insensitive, first match). No key → plain line."""
    if not key:
        return body
    lo, klo = body.lower(), _escape(key).lower()
    i = lo.find(klo)
    if i < 0:
        return body  # agent's key isn't in the text — draw the line plainly
    end = i + len(klo)
    return f"{body[:i]}{{\\1c{colour}}}{body[i:end]}{{\\r}}{body[end:]}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _wrap(text: str, max_chars: int) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _ass_time(t: float) -> str:
    t = max(t, 0.0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):d}:{int(m):02d}:{s:05.2f}"


TOOL = InsertsTool()
