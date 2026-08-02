"""Rebuild catalog.json from the designer's source decks, and one registry-item.json
per ported component.

The designer's three .dc.html files are the only authority on what the brand contains;
this script turns them into the inventory the editing agent reads. Run it after porting
a card — the catalog is generated, never hand-edited.

    python assets/brand/default/build_catalog.py

The registry-item.json schema was read off the live HyperFrames registry
(blocks/data-chart/registry-item.json, CLI v0.7.88), not from notes.
"""
import io
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source")
COMP = os.path.join(ROOT, "components")

# The Mono deck is the current numbered brandbook; the older "Бренд-система" deck still
# holds six cards the refresh dropped (02·A, 07·C, 07·D, 11, 12·B, 12·C) and is read
# second so the newer drawing of a shared number always wins.
SOURCES = [
    ("ИИмерсивный - Mono.dc.html", "mono"),
    ("ИИмерсивный - Акцентные плашки.dc.html", "accent"),
    ("Бренд-система ИИмерсивный.dc.html", "mono"),
]

# Routing decided in PLAN.local.md v4 phase 3 — recorded here so nobody ports them twice.
ROUTE = {
    # both were routed to ffmpeg in the plan; reading the actual markup corrected it
    "29": ("component", "alpha-оверлей: карточка ничего не увеличивает, окно только указывает. "
                        "Нужен зум самого кадра — это отдельное решение, punch в zooms.py"),
    "41": ("component", "alpha-оверлей: глитчатся только буквы (два призрака со сдвигом), "
                        "кадр под ними не трогается"),
    "09": ("deferred", "прогресс-бар опционален, длинный слой — до догфуда"),
    "07·A": ("component", "alpha-блок поверх стыка, transitions.py не трогать"),
    "07·B": ("component", "alpha-блок поверх стыка, transitions.py не трогать"),
    "42": ("component", "alpha-блок поверх стыка, transitions.py не трогать"),
}
ARCHIVED = {"D", "G"}                            # brand-manifest: accentOverlays.archived
NOT_DRAWN = ["22 таймлайн", "30 шаг N из M"]     # promised by the manifest, drawn nowhere

# A card header is always the same span trio: number, name, english hint.
HEAD = re.compile(
    r'color:#8A8A85">([^<]{1,8})</span>'
    r'<span style="font-weight:700;font-size:13px;color:#0B0B0C;letter-spacing:\.04em">([^<]*)</span>'
    r'<span[^>]*>([^<]*)</span>')
# The designer's spec for a card is the <sc-if> note right after it.
SPEC = re.compile(r'<sc-if[^>]*>.*?>([^<]*)</div></sc-if>', re.S)
TAG = re.compile(r'<[^>]+>')


def parse_deck(path):
    s = io.open(path, encoding="utf-8").read()
    for m in HEAD.finditer(s):
        num, name, hint = (x.strip() for x in m.groups())
        spec = SPEC.search(s, m.end())
        yield {"num": num, "name": name, "hint": hint,
               "spec": TAG.sub("", spec.group(1)).strip() if spec else ""}


def component_name(kind, num):
    """02·B -> mono-02b, A -> accent-a"""
    return f"{kind}-{num.replace('·', '').lower()}"


def read_component(name):
    path = os.path.join(COMP, name, "index.html")
    if not os.path.isfile(path):
        return None
    html = io.open(path, encoding="utf-8").read()
    variables = re.search(r"data-composition-variables='(\[.*?\])'", html, re.S)
    root = re.search(r'data-composition-id="([^"]+)"[^>]*data-duration="([^"]*)"', html, re.S)
    return {
        "html": html,
        "id": root.group(1) if root else name,
        "duration": float(root.group(2)) if root else None,
        "alpha": "background: transparent" in html or "background:transparent" in html,
        "variables": json.loads(variables.group(1)) if variables else [],
        "fonts": sorted(set(re.findall(r"url\('fonts/([^']+)'\)", html))),
        "assets": sorted(set(re.findall(r'src="(assets/[^"]+)"', html))),
    }


def build_cards():
    cards, seen = [], set()
    for fname, kind in SOURCES:
        for card in parse_deck(os.path.join(SRC, fname)):
            key = (kind, card["num"])
            if key in seen:      # the legacy deck repeats itself three times
                continue
            seen.add(key)
            name = component_name(kind, card["num"])
            comp = read_component(name)
            route, why = ROUTE.get(card["num"], ("component", None))
            if kind == "accent" and card["num"] in ARCHIVED:
                status = "archived"
            elif comp:
                status = "ready"
            elif route == "ffmpeg":
                status = "routed-ffmpeg"
            elif route == "deferred":
                status = "deferred"
            else:
                status = "todo"
            out = {"id": card["num"], "kind": kind, "name": card["name"],
                   "hint": card["hint"], "spec": card["spec"], "source": fname,
                   "status": status, "route": route}
            if why:
                out["routeNote"] = why
            if comp:
                out.update({
                    "component": f"components/{name}",
                    "compositionId": comp["id"],
                    "durationSec": comp["duration"],
                    "layer": "alpha" if comp["alpha"] else "opaque",
                    "variables": [{"id": v["id"], "label": v.get("label", ""),
                                   "default": v.get("default", "")} for v in comp["variables"]],
                })
            cards.append(out)
    cards.sort(key=lambda c: ({"mono": 0, "accent": 1}[c["kind"]], c["id"]))
    return cards


def write_catalog(cards):
    catalog = {
        "$comment": "Инвентарь бренда: каждая карточка, которую нарисовал дизайнер, зачем она "
                    "и — если уже собрана — какая композиция HyperFrames её рендерит. "
                    "Генерируется build_catalog.py из source/*.dc.html; руками не править.",
        "brand": "ИИмерсивный",
        "manifest": "brand-manifest.json",
        "counts": dict(Counter(c["status"] for c in cards), total=len(cards)),
        "notDrawn": NOT_DRAWN,
        "cards": cards,
    }
    with io.open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return catalog


def write_registry_items(cards):
    """Each ported component gets the manifest that makes it installable on its own."""
    written = 0
    for card in cards:
        if card["status"] != "ready":
            continue
        name = os.path.basename(card["component"])
        comp = read_component(name)
        files = [{"path": "index.html", "target": f"compositions/{name}.html",
                  "type": "hyperframes:composition"}]
        files += [{"path": f"fonts/{f}", "target": f"compositions/fonts/{f}",
                   "type": "hyperframes:asset"} for f in comp["fonts"]]
        files += [{"path": a, "target": f"compositions/{a}",
                   "type": "hyperframes:asset"} for a in comp["assets"]]
        item = {
            "$schema": "https://hyperframes.heygen.com/schema/registry-item.json",
            "name": name,
            "type": "hyperframes:block",
            "title": f'{card["id"]} {card["name"]}',
            "description": card["spec"],
            "tags": sorted({"immersive", card["kind"], card["layer"],
                            *re.findall(r"[a-z]+", card["hint"].lower())}),
            "dimensions": {"width": 1920, "height": 1080},
            "duration": card["durationSec"],
            "files": files,
        }
        path = os.path.join(COMP, name, "registry-item.json")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
            f.write("\n")
        written += 1
    return written


def check(cards):
    """The parser is regex over someone else's HTML — it fails silently or not at all."""
    ids = [(c["kind"], c["id"]) for c in cards]
    assert len(ids) == len(set(ids)), "duplicate card ids"
    assert len(cards) > 60, f"only {len(cards)} cards parsed — the deck markup changed"
    for c in cards:
        assert c["spec"], f'{c["id"]} {c["name"]}: spec did not parse'
        if c["status"] == "ready":
            assert os.path.isfile(os.path.join(ROOT, c["component"], "index.html"))
            assert c["durationSec"], f'{c["id"]}: no duration on the composition root'
    manifest = json.load(io.open(os.path.join(ROOT, "brand-manifest.json"), encoding="utf-8"))
    numbers = {c["id"].replace("·", "") for c in cards}
    mono = manifest["monoElements"]
    named = (mono["alwaysOn"] + mono["everyVideo"] + mono["onDemand"]
             + mono["transitions"]["ids"] + mono["static"]["ids"])
    for entry in named:
        head = entry.split()[0]
        assert any(n.startswith(head[:2]) for n in numbers), f"manifest names {entry}, no card"


if __name__ == "__main__":
    cards = build_cards()
    check(cards)
    catalog = write_catalog(cards)
    items = write_registry_items(cards)
    print(json.dumps(catalog["counts"], ensure_ascii=False), f"· registry-item.json × {items}")
