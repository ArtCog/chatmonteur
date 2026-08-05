"""Capability: ``stock`` — fetch B-roll/image candidates from free libraries.

The DECISION is the AGENT's job (D11): this tool only FETCHES candidates; the
agent then LOOKS at them, scores 1–5 (relevance / resolution / style / POV — see
``skills/motion.md``), rejects the wrong ones and re-queries with better terms.
Never overlay an unseen asset.

Providers, free-first (the selector pattern — no key → provider silently absent):

* ``openverse`` — CC images, **no key at all** (filtered to commercial-safe).
* ``pexels``    — photos+videos, free key in ``PEXELS_API_KEY``.
* ``pixabay``   — photos+videos, free key in ``PIXABAY_API_KEY``.
* ``imgflip``   — meme TEMPLATES (top-100, keyless; matched by name locally).
* ``freesound`` — SFX (kind ``sfx``), free token in ``FREESOUND_API_KEY``.

Candidates land in ``projects/<name>/assets/stock/<slug>/`` next to a
``manifest.json`` carrying provider/license/creator/source per file — CC-BY needs
attribution in the description; Pexels/Pixabay don't. Keep the manifest.

Keys are read through ``Config.get_secret`` (env, then ``.env``) — never ``os.environ``
alone, or a key that lives only in ``.env`` reads as "no provider available".
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult

_UA = {"User-Agent": "ChatMonteur/0.1 (github.com/ArtCog/chatmonteur)"}
# Candidates are downloaded in BATCHES for the agent to look at, and an overlay is
# drawn at =<0.7 of frame width (~1800 px on a 1440p render). Grabbing the 4K
# rendition of every candidate buys nothing and costs hundreds of megabytes.
_MIN_WIDTH = 1280
_TIMEOUT = 30


class StockTool(Tool):
    manifest = ToolManifest(
        name="stock_fetch",
        capability="stock",
        summary="Fetch stock/meme/SFX candidates (Openverse/Pexels/Pixabay/Imgflip/Freesound).",
        backends=("openverse", "pexels", "pixabay", "imgflip", "freesound"),
        requires_bin=(),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        query: str,
        kind: str = "image",           # image | video | meme | sfx
        count: int = 4,
        provider: str | None = None,   # force one; default = first available for kind
        min_width: int = _MIN_WIDTH,   # video: smallest rendition that is still enough
    ) -> ToolResult:
        if kind not in ("image", "video", "meme", "sfx"):
            raise ToolError(f"unknown kind {kind!r}; choose image, video, meme or sfx")
        count = max(1, min(int(count), 10))
        secret = ctx.config.get_secret          # env first, then .env — never os.environ alone
        providers = _providers_for(kind, provider, secret)
        if not providers:
            raise ToolError(_no_provider_hint(kind))

        out_dir = ctx.paths.assets / "stock" / _slug(query)
        out_dir.mkdir(parents=True, exist_ok=True)
        entries: list[dict] = []
        errors: list[str] = []
        for name in providers:
            try:
                entries = _FETCHERS[name](query, kind, count, out_dir,
                                          secret(f"{name.upper()}_API_KEY") or "", min_width)
            except Exception as exc:  # noqa: BLE001 — a dead provider must not kill the run
                errors.append(f"{name}: {exc}")
                continue
            if entries:
                break
        if not entries:
            raise ToolError(
                f"no candidates for {query!r} ({kind}); tried {', '.join(providers)}"
                + (f" — errors: {'; '.join(errors)}" if errors else "")
                + ". Re-query with different terms (lead with the subject, add a POV keyword)."
            )

        manifest = out_dir / "manifest.json"
        manifest.write_text(json.dumps({"query": query, "candidates": entries},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
        ctx.log(f"stock: {len(entries)} candidates from {entries[0]['provider']} → {out_dir}")
        ctx.log("stock: LOOK at every candidate and score 1–5 before using any (motion.md)")
        return ToolResult(
            artifacts={"dir": str(out_dir), "manifest": str(manifest)},
            meta={"count": len(entries), "provider": entries[0]["provider"]},
        )


# --- provider selection ---------------------------------------------------------

def _providers_for(kind: str, forced: str | None, secret=None) -> list[str]:
    """``secret`` is ``Config.get_secret`` — the ONLY thing that can see ``.env``.

    Without it a key sitting in ``.env`` (where the keys actually live) reads as
    "no provider available", and the tool blames the user for not having a key.
    """
    order = {
        "image": ["openverse", "pexels", "pixabay"],
        "video": ["pexels", "pixabay"],
        "meme": ["imgflip"],
        "sfx": ["freesound"],
    }[kind]
    if forced:
        if forced not in order:
            raise ToolError(f"provider {forced!r} can't serve kind {kind!r} (options: {order})")
        order = [forced]
    secret = secret or os.environ.get
    return [p for p in order if _available(p, secret)]


def _available(provider: str, secret) -> bool:
    if provider in ("openverse", "imgflip"):
        return True  # keyless
    return bool(secret(f"{provider.upper()}_API_KEY"))


def _no_provider_hint(kind: str) -> str:
    return (
        f"no provider available for kind {kind!r}. Free keys unlock more: "
        "PEXELS_API_KEY (pexels.com/api) and PIXABAY_API_KEY (pixabay.com/api/docs) in .env."
    )


# --- fetchers (query -> downloaded files + manifest entries) --------------------

def _fetch_openverse(query: str, kind: str, count: int, out_dir: pathlib.Path,
                     key: str = "", min_width: int = _MIN_WIDTH) -> list[dict]:
    q = urllib.parse.urlencode({
        "q": query, "page_size": count,
        "license_type": "commercial",  # MIT-safe: only commercial-use licenses
    })
    data = _get_json(f"https://api.openverse.org/v1/images/?{q}")
    entries = []
    for i, r in enumerate(data.get("results", [])[:count]):
        f = _download(r["url"], out_dir, f"openverse_{i + 1}")
        if f:
            entries.append({
                "file": str(f), "provider": "openverse",
                "license": r.get("license", "cc"), "creator": r.get("creator", ""),
                "source": r.get("foreign_landing_url", ""),
                "attribution_required": not str(r.get("license", "")).startswith(("cc0", "pdm")),
            })
    return entries


def _fetch_pexels(query: str, kind: str, count: int, out_dir: pathlib.Path,
                  key: str = "", min_width: int = _MIN_WIDTH) -> list[dict]:
    base = "https://api.pexels.com/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
    q = urllib.parse.urlencode({"query": query, "per_page": count})
    data = _get_json(f"{base}?{q}", headers={"Authorization": key})
    entries = []
    items = data.get("videos" if kind == "video" else "photos", [])[:count]
    for i, r in enumerate(items):
        if kind == "video":
            url = _pexels_file(r.get("video_files", []), min_width)
        else:
            url = r.get("src", {}).get("large2x")
        f = _download(url, out_dir, f"pexels_{i + 1}") if url else None
        if f:
            entries.append({"file": str(f), "provider": "pexels", "license": "pexels",
                            "creator": r.get("photographer") or r.get("user", {}).get("name", ""),
                            "source": r.get("url", ""), "attribution_required": False})
    return entries


def _fetch_pixabay(query: str, kind: str, count: int, out_dir: pathlib.Path,
                   key: str = "", min_width: int = _MIN_WIDTH) -> list[dict]:
    base = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
    q = urllib.parse.urlencode({"key": key, "q": query, "per_page": count, "safesearch": "true"})
    data = _get_json(f"{base}?{q}")
    entries = []
    for i, r in enumerate(data.get("hits", [])[:count]):
        if kind == "video":
            vids = r.get("videos", {})
            url = (vids.get("large") or vids.get("medium") or {}).get("url")
        else:
            url = r.get("largeImageURL")
        f = _download(url, out_dir, f"pixabay_{i + 1}") if url else None
        if f:
            entries.append({"file": str(f), "provider": "pixabay", "license": "pixabay",
                            "creator": r.get("user", ""), "source": r.get("pageURL", ""),
                            "attribution_required": False})
    return entries


def _fetch_imgflip(query: str, kind: str, count: int, out_dir: pathlib.Path,
                   key: str = "", min_width: int = _MIN_WIDTH) -> list[dict]:
    data = _get_json("https://api.imgflip.com/get_memes")
    memes = data.get("data", {}).get("memes", [])
    matches = _match_memes(memes, query)[:count]
    entries = []
    for i, m in enumerate(matches):
        f = _download(m["url"], out_dir, f"imgflip_{i + 1}")
        if f:
            entries.append({"file": str(f), "provider": "imgflip", "license": "meme-template",
                            "creator": "", "source": m["url"], "name": m["name"],
                            "attribution_required": False})
    return entries


def _pexels_file(files: list[dict], min_width: int = _MIN_WIDTH) -> str | None:
    """The SMALLEST rendition that still clears ``min_width`` — or the biggest one
    available when every rendition falls short.

    WIDTH, not height: an overlay is scaled to a fraction of the frame WIDTH
    (``scale=target_w:-2``) and so is a full-frame background. Judging by height
    passes a 720x1280 vertical clip off as "1080p" — caught on a live fetch.
    """
    ranked = sorted(files, key=lambda v: v.get("width") or 0)
    enough = [v for v in ranked if (v.get("width") or 0) >= min_width]
    pick = enough[0] if enough else (ranked[-1] if ranked else None)
    return pick["link"] if pick else None


def _fetch_freesound(query: str, kind: str, count: int, out_dir: pathlib.Path,
                     key: str = "", min_width: int = _MIN_WIDTH) -> list[dict]:
    """SFX candidates. The MP3 preview is what we download on purpose: the original
    file needs an OAuth2 dance, and a preview is 128 kbps of a two-second whoosh that
    is about to sit 15 dB under speech. Promote to the original only if one is ever
    audibly short."""
    q = urllib.parse.urlencode({
        "query": query, "page_size": count, "sort": "rating_desc",
        "fields": "id,name,duration,license,username,url,previews",
        "filter": f"license:({_LICENCES})",
    })
    data = _get_json(f"https://freesound.org/apiv2/search/text/?{q}", headers={"Authorization": f"Token {key}"})
    entries = []
    for i, r in enumerate(data.get("results", [])[:count]):
        url = (r.get("previews") or {}).get("preview-hq-mp3")
        f = _download(url, out_dir, f"freesound_{i + 1}") if url else None
        if f:
            attribution, noncommercial = _licence_flags(r.get("license", ""))
            entries.append({"file": str(f), "provider": "freesound", "license": r.get("license", ""),
                            "creator": r.get("username", ""), "source": r.get("url", ""),
                            "name": r.get("name", ""), "duration_sec": round(r.get("duration", 0), 2),
                            "preview_only": True,
                            "attribution_required": attribution, "noncommercial": noncommercial})
    return entries


# Артур 2026-08-05: канал не монетизируется, поэтому NC-материал допустим. Помечаем
# его флагом, чтобы при подключении монетизации было что перебрать, а не искать заново.
_LICENCES = '"Creative Commons 0" OR "Attribution" OR "Attribution Noncommercial"'


def _licence_flags(licence_url: str) -> tuple[bool, bool]:
    """(нужна атрибуция, ограничена коммерция) по ссылке на лицензию."""
    u = licence_url.lower()
    if "publicdomain/zero" in u or "/cc0" in u:
        return False, False
    return True, ("by-nc" in u or "sampling" in u)


def _match_memes(memes: list[dict], query: str) -> list[dict]:
    """Rank the top-100 templates by name-token overlap with the query (keyless API
    has no search endpoint). All query tokens present → best; then any-token hits."""
    tokens = [t for t in re.split(r"\W+", query.lower()) if t]
    scored = []
    for m in memes:
        name = m.get("name", "").lower()
        hits = sum(1 for t in tokens if t in name)
        if hits:
            scored.append((hits == len(tokens), hits, m))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [m for _, _, m in scored]


def _slug(query: str) -> str:
    return re.sub(r"[^a-z0-9а-яё]+", "-", query.lower()).strip("-")[:60] or "query"


# --- plumbing -------------------------------------------------------------------

def _get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={**_UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(url: str, out_dir: pathlib.Path, stem: str) -> pathlib.Path | None:
    ext = pathlib.Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
    target = out_dir / f"{stem}{ext}"
    req = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp, open(target, "wb") as f:
            f.write(resp.read())
    except Exception:  # noqa: BLE001 — one dead link shouldn't sink the batch
        return None
    return target


_FETCHERS = {
    "openverse": _fetch_openverse,
    "pexels": _fetch_pexels,
    "pixabay": _fetch_pixabay,
    "imgflip": _fetch_imgflip,
    "freesound": _fetch_freesound,
}

TOOL = StockTool()
