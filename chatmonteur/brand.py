"""The brand system, read from one place.

Every on-screen element — captions, meaning-inserts, lower-thirds, motion components —
must agree on the same colours and typefaces. Until now each tool carried its own copy of
the accent hex and ``"Golos Text"``, which guarantees the day a token changes and the
captions quietly keep the old one. That is not hypothetical: the brandbook dropped its
green accent and tokens.css kept it for weeks.

**``assets/brand/<name>/tokens.css`` is the source of truth**, and it already existed: the
HyperFrames compositions link it as ordinary CSS. So this parses that same file rather than
introducing a second format for Python to disagree with. One file, two consumers — a designer
edits a token and both the burned captions and the rendered components follow.

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
import pathlib
import re

from .core.errors import ToolError

_BRAND_ROOT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "brand"
_TOKEN_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);", re.IGNORECASE)
# `--font-sans: 'Golos Text', system-ui, sans-serif` → the family actually bundled.
_FIRST_FAMILY = re.compile(r"^\s*'([^']+)'|^\s*\"([^\"]+)\"")


@functools.lru_cache(maxsize=4)
def tokens(name: str = "default") -> dict[str, str]:
    """Every ``--token: value`` from that brand's ``tokens.css``, keys without the dashes."""
    path = _BRAND_ROOT / name / "tokens.css"
    if not path.is_file():
        raise ToolError(f"brand '{name}' has no tokens.css at {path}")
    text = path.read_text(encoding="utf-8")
    found = {k.lower(): v.strip() for k, v in _TOKEN_RE.findall(text)}
    if not found:
        raise ToolError(f"{path} defines no --tokens")
    return found


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
    return _BRAND_ROOT / brand / "fonts"


def available() -> list[str]:
    """Brands that can actually be loaded (a directory carrying a tokens.css)."""
    if not _BRAND_ROOT.is_dir():
        return []
    return sorted(p.name for p in _BRAND_ROOT.iterdir() if (p / "tokens.css").is_file())
