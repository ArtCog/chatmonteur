"""The brand system, read from one place.

Every on-screen element — captions, meaning-inserts, lower-thirds, motion components —
must agree on the same colours and typefaces. Until now each tool carried its own copy of
the accent hex and ``"Golos Text"``, which guarantees the day a token changes and the
captions quietly keep the old one. That is not hypothetical: the brandbook dropped its
green accent and tokens.css kept it for weeks.

**``assets/brand/<name>/frame.md`` is the visual source of truth**, using HyperFrames'
native design-spec format. ``tokens.css`` is its runtime CSS projection for Python,
ffmpeg/libass, and standalone registry blocks. The pack validator refuses drift between
the two rather than introducing another visual-brand schema.

    from .. import brand
    brand.colour("accent-hype")   # '#FF5B2E'
    brand.ass("caption-accent")   # '&H00D7FF&'   — libass wants BGR
    brand.font("sans")            # 'Golos Text'

There is deliberately no single ``--accent``: the brandbook is monochrome, its three
accent colours are named for what they mean, and the caption colour is separate from
all of them so a brandbook change cannot silently repaint burned-in captions.

ASS colours are the reason this needs code and not a constant: libass writes colour as
**BGR**, byte-reversed from the hex a designer hands you. Reversing by hand is how a green
accent ships as blue.
"""

from __future__ import annotations

import functools
import io
import json
import pathlib
import re
from typing import Any, cast

import yaml

from .core.errors import ToolError

_PACKAGE_BRAND_ROOT = pathlib.Path(__file__).resolve().parent / "assets" / "brand"
_SOURCE_BRAND_ROOT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "brand"
# Wheels carry the packs inside ``chatmonteur``. A source checkout keeps the
# authoring tree at repository level so designers can work on it directly.
_BRAND_ROOT = _PACKAGE_BRAND_ROOT if _PACKAGE_BRAND_ROOT.is_dir() else _SOURCE_BRAND_ROOT
_TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);", re.IGNORECASE)
# `--font-sans: 'Golos Text', system-ui, sans-serif` → the family actually bundled.
_FIRST_FAMILY = re.compile(r"^\s*'([^']+)'|^\s*\"([^\"]+)\"")
_PACK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RGBA = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})"
    r"(?:\s*,\s*(0(?:\.\d+)?|1(?:\.0+)?|\.\d+))?\s*\)",
    re.IGNORECASE,
)
_FRAME_COLOUR_TOKENS = {
    "ink": "ink", "paper": "paper", "surface": "surface",
    "surfaceRaised": "surface-2", "cardDark": "card-dark",
    "cardDarkBorder": "card-dark-border", "secondaryText": "gray-1",
    "labels": "gray-2", "dividerDark": "gray-3", "dividerLight": "line",
    "accentHype": "accent-hype", "accentDanger": "accent-danger",
    "accentInsight": "accent-insight", "captionAccent": "caption-accent",
    "captionScrim": "scrim", "insertAccentOnPaper": "insert-accent-on-paper",
}


def root(name: str = "default") -> pathlib.Path:
    """Return one direct child of the brand-pack root; traversal is never valid."""
    if not isinstance(name, str) or not _PACK_NAME.fullmatch(name):
        raise ToolError(f"invalid brand name {name!r}; use letters, numbers, dot, dash, or underscore")
    return _BRAND_ROOT / name


def _json_file(name: str, filename: str) -> dict:
    path = root(name) / filename
    if not path.is_file():
        raise ToolError(f"brand '{name}' has no {filename} at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"brand '{name}' has invalid {filename}: {exc}") from exc
    if not isinstance(data, dict):
        raise ToolError(f"brand '{name}' {filename} must contain a JSON object")
    return data


@functools.lru_cache(maxsize=4)
def frame(name: str = "default") -> dict:
    """Parse the normative YAML frontmatter from HyperFrames' native ``frame.md``."""
    path = root(name) / "frame.md"
    if not path.is_file():
        raise ToolError(f"brand '{name}' has no HyperFrames frame.md at {path}")
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.DOTALL)
    if not match:
        raise ToolError(f"brand '{name}' frame.md needs YAML frontmatter between --- markers")
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ToolError(f"brand '{name}' has invalid frame.md frontmatter: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("colors"), dict):
        raise ToolError(f"brand '{name}' frame.md must define a colors mapping")
    if not isinstance(data.get("typography"), dict):
        raise ToolError(f"brand '{name}' frame.md must define a typography mapping")
    return data


def load_pack(name: str = "default") -> tuple[dict, dict]:
    """Load the renderable half of a pack: component catalog plus policy manifest."""
    validate_runtime(name)
    catalog = _json_file(name, "catalog.json")
    manifest = _json_file(name, "brand-manifest.json")
    if not isinstance(catalog.get("cards"), list):
        raise ToolError(f"brand '{name}' catalog.json must define a cards list")
    return catalog, manifest


def validate_runtime(name: str = "default") -> None:
    """Refuse a CSS projection that has drifted from native ``frame.md`` values."""
    spec = frame(name)
    runtime = tokens(name)

    def same(left: object, right: object) -> bool:
        def normal(value: object) -> str:
            compact = str(value).replace(" ", "").casefold()
            return re.sub(r"(?<=[,(])\.(?=\d)", "0.", compact)

        return normal(left) == normal(right)

    for frame_key, token_key in _FRAME_COLOUR_TOKENS.items():
        if frame_key not in spec["colors"]:
            continue
        if token_key not in runtime or not same(spec["colors"][frame_key], runtime[token_key]):
            raise ToolError(
                f"brand '{name}' frame.md colors.{frame_key} is {spec['colors'][frame_key]!r}, "
                f"but tokens.css --{token_key} is {runtime.get(token_key)!r}"
            )

    for role, details in spec["typography"].items():
        if not isinstance(details, dict) or "family" not in details:
            continue
        token_key = f"font-{role}"
        value = runtime.get(token_key, "")
        if str(details["family"]).casefold() not in value.casefold():
            raise ToolError(
                f"brand '{name}' frame.md typography.{role}.family is {details['family']!r}, "
                f"but tokens.css --{token_key} is {value!r}"
            )


def component(name: str, relative: str) -> pathlib.Path:
    """Resolve a catalog component path inside its pack and require its entry point."""
    pack_root = root(name).resolve()
    path = (pack_root / relative / "index.html").resolve()
    try:
        path.relative_to(pack_root)
    except ValueError as exc:
        raise ToolError(f"brand '{name}' component escapes its pack: {relative!r}") from exc
    if not path.is_file():
        raise ToolError(f"brand '{name}' component is missing: {path}")
    return path


@functools.lru_cache(maxsize=4)
def tokens(name: str = "default") -> dict[str, str]:
    """Every ``--token: value`` from that brand's ``tokens.css``, keys without the dashes."""
    path = root(name) / "tokens.css"
    if not path.is_file():
        raise ToolError(f"brand '{name}' has no tokens.css at {path}")
    text = path.read_text(encoding="utf-8")
    found = {k.lower(): v.strip() for k, v in _TOKEN_RE.findall(text)}
    if not found:
        raise ToolError(f"{path} defines no --tokens")
    return found


@functools.lru_cache(maxsize=4)
def channel(name: str = "default") -> dict:
    """Public channel identities used by on-screen CTAs and generated QR codes."""
    path = root(name) / "channel.json"
    if not path.is_file():
        raise ToolError(f"brand '{name}' has no channel.json at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("telegram"), dict):
        raise ToolError(f"{path} must define a telegram object")
    return data


def telegram_qr_png(name: str = "default", *, size: int = 540) -> bytes:
    """Render the brand's canonical Telegram channel as a deterministic QR PNG."""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - setup error, not an editing branch
        raise ToolError("QR asset generation needs the dev dependencies: pip install -e .[dev]") from exc

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(channel(name)["telegram"]["url"])
    qr.make(fit=True)
    image = cast(Any, qr.make_image(
        fill_color=colour("ink", brand=name),
        back_color=colour("paper", brand=name),
    )).convert("RGB")
    image = image.resize((size, size), Image.Resampling.NEAREST)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def token(key: str, *, brand: str = "default") -> str:
    table = tokens(brand)
    if key not in table:
        raise ToolError(f"brand '{brand}' has no token '{key}'; known: {sorted(table)}")
    return table[key]


def colour(key: str, *, brand: str = "default") -> str:
    """A token's value as ``#RRGGBB``. Raises if the token isn't a plain hex colour."""
    value = token(key, brand=brand)
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ToolError(f"brand token '{key}' is {value!r}, not a #RRGGBB colour")
    return value.upper()


def rgba(key: str, *, brand: str = "default") -> tuple[int, int, int, float]:
    """Return a CSS ``#RRGGBB``/``rgb()``/``rgba()`` token as RGBA values."""
    value = token(key, brand=brand).strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 1.0
    match = _RGBA.fullmatch(value)
    if not match:
        raise ToolError(f"brand token '{key}' is {value!r}, not a CSS RGB colour")
    red, green, blue = (int(match.group(i)) for i in range(1, 4))
    if any(channel > 255 for channel in (red, green, blue)):
        raise ToolError(f"brand token '{key}' has an RGB channel outside 0..255")
    opacity = float(match.group(4)) if match.group(4) is not None else 1.0
    return red, green, blue, opacity


def ass_override(key: str, *, brand: str = "default") -> str:
    """A CSS colour token as an inline ASS ``\\1c``/``\\3c`` BGR value."""
    red, green, blue, _ = rgba(key, brand=brand)
    return f"&H{blue:02X}{green:02X}{red:02X}&"


def ass_style(key: str, *, brand: str = "default", alpha: int | None = None) -> str:
    """A CSS colour token as an ASS style field, preserving CSS opacity by default."""
    red, green, blue, opacity = rgba(key, brand=brand)
    resolved_alpha = round((1.0 - opacity) * 255) if alpha is None else alpha
    if not 0 <= resolved_alpha <= 255:
        raise ToolError(f"ASS alpha must be in 0..255, got {resolved_alpha}")
    return f"&H{resolved_alpha:02X}{blue:02X}{green:02X}{red:02X}"


def ass(key: str, *, brand: str = "default", alpha: int | None = None) -> str:
    """A token as an ASS colour override, e.g. ``&H6AE82B&``.

    libass stores colour BYTE-REVERSED (BGR), so ``#FF5B2E`` becomes ``&H2E5BFF&``. Pass
    ``alpha`` (0 opaque … 255 invisible) for the ``&HAABBGGRR`` style-field form used by
    shadows and plates.
    """
    r, g, b = colour(key, brand=brand)[1:3], colour(key, brand=brand)[3:5], colour(key, brand=brand)[5:7]
    if alpha is None:
        return f"&H{b}{g}{r}&"
    return f"&H{alpha:02X}{b}{g}{r}"


def font(role: str = "sans", *, brand: str = "default") -> str:
    """The family name for ``sans`` / ``mono`` / ``serif``, as libass will look it up."""
    value = token(f"font-{role}", brand=brand)
    match = _FIRST_FAMILY.match(value)
    if not match:
        raise ToolError(f"brand token 'font-{role}' is {value!r}; expected a quoted family first")
    return match.group(1) or match.group(2)


def font_dir(brand: str = "default") -> pathlib.Path:
    """Where the bundled TTFs live — ffmpeg needs this passed to libass explicitly."""
    return root(brand) / "fonts"


def available() -> list[str]:
    """Installed packs carrying both the native design spec and runtime tokens."""
    if not _BRAND_ROOT.is_dir():
        return []
    return sorted(
        p.name for p in _BRAND_ROOT.iterdir()
        if (p / "frame.md").is_file() and (p / "tokens.css").is_file()
    )
