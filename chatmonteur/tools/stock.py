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

Candidates land in ``projects/<name>/assets/stock/<slug>/`` next to a
``manifest.json`` carrying provider/license/creator/source per file — CC-BY needs
attribution in the description; Pexels/Pixabay don't. Keep the manifest.
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
_TIMEOUT = 30


class StockTool(Tool):
    manifest = ToolManifest(
        name="stock_fetch",
        capability="stock",
        summary="Fetch stock/meme candidates (Openverse/Pexels/Pixabay/Imgflip) for agent scoring.",
        backends=("openverse", "pexels", "pixabay", "imgflip"),
        requires_bin=(),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        query: str,
        kind: str = "image",           # image | video | meme
        count: int = 4,
        provider: str | None = None,   # force one; default = first available for kind
    ) -> ToolResult:
        if kind not in ("image", "video", "meme"):
            raise ToolError(f"unknown kind {kind!r}; choose image, video or meme")
        count = max(1, min(int(count), 10))
        providers = _providers_for(kind, provider)
        if not providers:
            raise ToolError(_no_provider_hint(kind))

        out_dir = ctx.paths.assets / "stock" / _slug(query)
        out_dir.mkdir(parents=True, exist_ok=True)
        entries: list[dict] = []
        errors: list[str] = []
        for name in providers:
            try:
                entries = _FETCHERS[name](query, kind, count, out_dir)
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

def _providers_for(kind: str, forced: str | None) -> list[str]:
    order = {
        "image": ["openverse", "pexels", "pixabay"],
        "video": ["pexels", "pixabay"],
        "meme": ["imgflip"],
    }[kind]
    if forced:
        if forced not in order:
            raise ToolError(f"provider {forced!r} can't serve kind {kind!r} (options: {order})")
        order = [forced]
    return [p for p in order if _available(p)]


def _available(provider: str) -> bool:
    if provider in ("openverse", "imgflip"):
        return True  # keyless
    return bool(os.environ.get(f"{provider.upper()}_API_KEY"))


def _no_provider_hint(kind: str) -> str:
    return (
        f"no provider available for kind {kind!r}. Free keys unlock more: "
        "PEXELS_API_KEY (pexels.com/api) and PIXABAY_API_KEY (pixabay.com/api/docs) in .env."
    )


# --- fetchers (query -> downloaded files + manifest entries) --------------------

def _fetch_openverse(query: str, kind: str, count: int, out_dir: pathlib.Path) -> list[dict]:
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


def _fetch_pexels(query: str, kind: str, count: int, out_dir: pathlib.Path) -> list[dict]:
    key = os.environ["PEXELS_API_KEY"]
    base = "https://api.pexels.com/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
    q = urllib.parse.urlencode({"query": query, "per_page": count})
    data = _get_json(f"{base}?{q}", headers={"Authorization": key})
    entries = []
    items = data.get("videos" if kind == "video" else "photos", [])[:count]
    for i, r in enumerate(items):
        if kind == "video":
            files = sorted(r.get("video_files", []), key=lambda v: v.get("height") or 0, reverse=True)
            url = files[0]["link"] if files else None
        else:
            url = r.get("src", {}).get("large2x")
        f = _download(url, out_dir, f"pexels_{i + 1}") if url else None
        if f:
            entries.append({"file": str(f), "provider": "pexels", "license": "pexels",
                            "creator": r.get("photographer") or r.get("user", {}).get("name", ""),
                            "source": r.get("url", ""), "attribution_required": False})
    return entries


def _fetch_pixabay(query: str, kind: str, count: int, out_dir: pathlib.Path) -> list[dict]:
    key = os.environ["PIXABAY_API_KEY"]
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


def _fetch_imgflip(query: str, kind: str, count: int, out_dir: pathlib.Path) -> list[dict]:
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
}

TOOL = StockTool()
