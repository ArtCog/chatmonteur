"""Capability: ``contact_sheet`` — show the visual plan as ONE scrollable page.

The phase-③ gate used to be "here is storyboard.json, approve it". Артур
2026-08-01: the gate is **one HTML page — frame + phrase + timecode, scrolls in a
minute**. A JSON plan cannot be judged; a contact sheet can, because it puts the
candidate picture next to the words it will cover.

Rules this encodes (`bank-grill-decisions-2026-08-01.md`, decision 4):

* **One candidate per slot.** Not two or three alternatives per beat — that was
  killed in the counter-grill. A second round happens only on the beats the
  reviewer marks as wrong.
* **Filler owes a sentence.** Any beat filled with background material from the
  bank carries a one-line justification ("looked for a screenshot of X, there is
  no official one" / "connective tissue between blocks"). There is no ceiling on
  how much filler a video may use — instead there is the duty to explain, and a
  page full of "found nothing" reads as the diagnosis of laziness it is.

The page is self-contained (thumbnails inlined as data URIs), so it can be moved,
mailed or opened from anywhere without dragging a folder of images along.
"""

from __future__ import annotations

import base64
import html
import json
import pathlib
import tempfile

from ..core.context import RunContext
from ..core.errors import ToolError
from ..core.tool import Tool, ToolManifest, ToolResult
from .. import media

_SECTIONS = ("zooms", "overlays", "inserts", "motion")
_THUMB_W = 360
# Bank folders whose material is background, not evidence — these owe a "why".
_FILLER_DIRS = ("bank/gameplay", "bank/thematic")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class ContactSheetTool(Tool):
    manifest = ToolManifest(
        name="contact_sheet_html",
        capability="contact_sheet",
        summary="Render the storyboard as one scrollable HTML page for the visual gate.",
        backends=("ffmpeg",),
        requires_bin=("ffmpeg",),
        cost="free",
    )

    def run(
        self,
        ctx: RunContext,
        *,
        input: str,
        storyboard: str,
        transcript: str | None = None,
    ) -> ToolResult:
        media.require("ffmpeg")
        sb_path = pathlib.Path(storyboard)
        if not sb_path.is_file():
            raise ToolError(f"contact_sheet: storyboard not found: {sb_path}")
        data = json.loads(sb_path.read_text(encoding="utf-8"))

        beats = _beats(data)
        if not beats:
            raise ToolError(
                "contact_sheet: the storyboard has no visual events — there is nothing "
                "to review. Plan the pass first."
            )

        tr_path = pathlib.Path(transcript) if transcript else ctx.paths.transcripts / "master.json"
        segments = _segments(tr_path)
        if not segments:
            ctx.log(f"contact_sheet: no transcript at {tr_path} — the sheet will carry "
                    "pictures without the words they cover")

        with tempfile.TemporaryDirectory() as tmp:
            for i, b in enumerate(beats):
                b["thumb"] = _thumb(b, input, pathlib.Path(tmp) / f"{i}.jpg", log=ctx.log)
                b["said"] = _said_at(segments, b["start"])

        out = ctx.paths.transcripts / "contact-sheet.html"
        out.write_text(_page(beats, ctx.project), encoding="utf-8")

        owed = [b for b in beats if b["is_filler"] and not b["why"]]
        if owed:
            ctx.log(f"⚠ contact_sheet: {len(owed)} filler beat(s) carry no reason — add a "
                    "'why' to each, an unexplained fill reads as laziness")
        missing = [b for b in beats if b["missing"]]
        ctx.log(f"contact_sheet: {len(beats)} beats → {out}")
        return ToolResult(
            artifacts={"contact_sheet": str(out)},
            meta={"beats": len(beats), "filler_without_reason": len(owed),
                  "missing_assets": len(missing)},
        )


def _beats(data: dict) -> list[dict]:
    """Flatten every planned event into one time-ordered review list."""
    beats = []
    for section in _SECTIONS:
        for item in data.get(section) or []:
            file = str(item.get("file", "") or "")
            beats.append({
                "section": section,
                "start": float(item["start"]),
                "end": float(item.get("end", item["start"])),
                "what": _describe(section, item),
                "file": file,
                "why": str(item.get("why", "") or "").strip(),
                "is_filler": _is_filler(file),
                # A declared asset that isn't on disk must SAY so. Falling back to
                # the footage underneath would show the reviewer a picture that is
                # not the candidate, and they would approve a beat that cannot burn.
                "missing": bool(file) and not pathlib.Path(file).is_file(),
                # Filled in by run(); defaulted here so the page renders from a
                # bare plan too — a sheet without pictures still beats raw JSON.
                "thumb": "",
                "said": "",
            })
    return sorted(beats, key=lambda b: b["start"])


def _describe(section: str, item: dict) -> str:
    if section == "inserts":
        return str(item.get("text", "")) or "(insert without text)"
    if section == "motion":
        return str(item.get("name", "")) or "(motion graphic)"
    if section == "zooms":
        reason = item.get("reason")
        shot = f"{item.get('kind', 'punch')} ×{item.get('scale', '?')}"
        return f"{shot} — {reason}" if reason else shot
    return pathlib.PurePath(str(item.get("file", ""))).name or "(overlay without file)"


def _is_filler(file: str) -> bool:
    slashed = file.replace("\\", "/").lower()
    return any(d in slashed for d in _FILLER_DIRS)


def _thumb(beat: dict, video: str, dst: pathlib.Path, *, log) -> str:
    """One data-URI thumbnail: the visible result at this beat.

    An overlay's candidate is the picture going in, not the footage under it — so
    ordinary overlay assets are shown alone. A motion snapshot is different: it is
    a full-canvas layer and may carry alpha, so showing it on the page's black body
    lies about what will be approved. Composite motion images over the actual frame.
    Zooms and inserts have nothing of their own, and their candidate IS that frame.
    """
    if beat["missing"]:
        log(f"⚠ contact_sheet: {beat['file']} is planned at {beat['start']:.1f}s but is "
            "not on disk — the sheet will show the gap instead of the footage under it")
        return ""

    src, seek = video, beat["start"]
    asset = pathlib.Path(beat["file"]) if beat["file"] else None
    if asset:
        src, seek = str(asset), (0.0 if asset.suffix.lower() in _IMAGE_SUFFIXES else 0.5)

    try:
        if beat["section"] == "motion" and asset and asset.suffix.lower() in _IMAGE_SUFFIXES:
            width, height = _video_wh(video)
            media.run([
                "ffmpeg", "-v", "error", "-y",
                "-ss", f"{max(0.0, beat['start']):.3f}", "-i", video,
                "-i", str(asset),
                "-filter_complex",
                f"[1:v]scale={width}:{height}[layer];"
                f"[0:v][layer]overlay=0:0,scale={_THUMB_W}:-2",
                "-frames:v", "1", str(dst),
            ])
        else:
            media.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, seek):.3f}", "-i", src,
                 "-frames:v", "1", "-vf", f"scale={_THUMB_W}:-2", str(dst)]
            )
        return "data:image/jpeg;base64," + base64.b64encode(dst.read_bytes()).decode("ascii")
    except (ToolError, OSError):
        log(f"contact_sheet: no frame at {beat['start']:.1f}s from {pathlib.PurePath(src).name}")
        return ""


def _video_wh(path: str) -> tuple[int, int]:
    for stream in media.ffprobe_json(path).get("streams", []):
        if stream.get("codec_type") == "video" and stream.get("width") and stream.get("height"):
            return int(stream["width"]), int(stream["height"])
    return 1920, 1080


def _segments(path: pathlib.Path) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("segments") or []
    except (OSError, ValueError):
        return []


def _said_at(segments: list[dict], t: float) -> str:
    """What is being said when this beat lands — the words the picture must serve."""
    for s in segments:
        if float(s["start"]) <= t < float(s["end"]):
            return str(s.get("text", "")).strip()
    return ""


def _tc(seconds: float) -> str:
    return f"{int(seconds) // 60:d}:{int(seconds) % 60:02d}"


_CSS = """
:root { color-scheme: dark }
body { margin:0; background:#0B0B0C; color:#FAFAF7;
       font:15px/1.5 ui-sans-serif,system-ui,Segoe UI,sans-serif }
header { padding:28px 32px 16px; border-bottom:1px solid #26262A }
h1 { margin:0 0 6px; font-size:20px; font-weight:600 }
.sub { color:#8A8A90; font-size:13px }
ol { list-style:none; margin:0; padding:0 }
li { display:grid; grid-template-columns:360px 1fr; gap:24px;
     padding:20px 32px; border-bottom:1px solid #1C1C20; align-items:start }
img { width:360px; border-radius:8px; display:block; background:#161618 }
.blank { width:360px; aspect-ratio:16/9; border-radius:8px; background:#161618;
         display:grid; place-items:center; color:#5A5A60; font-size:12px }
.gone { color:#FF5B2E; border:1px dashed #55251A }
.meta { display:flex; gap:10px; align-items:baseline; margin-bottom:8px }
.tc { font:600 13px ui-monospace,Consolas,monospace; color:#FAFAF7 }
.kind { font:11px ui-monospace,Consolas,monospace; letter-spacing:.08em;
        text-transform:uppercase; color:#8A8A90 }
.what { font-size:16px; margin:0 0 10px }
.said { color:#A8A8AE; font-style:italic; margin:0 0 10px }
.why { color:#8A8A90; font-size:13px; margin:0 }
.owed { color:#FF5B2E; font-size:13px; margin:0 }
"""


def _page(beats: list[dict], project: str) -> str:
    rows = []
    for b in beats:
        if b["thumb"]:
            thumb = f'<img src="{b["thumb"]}" alt="">'
        elif b["missing"]:
            thumb = '<div class="blank gone">файла нет на диске</div>'
        else:
            thumb = '<div class="blank">кадр не снят</div>'
        said = f'<p class="said">«{html.escape(b["said"])}»</p>' if b["said"] else ""
        if b["why"]:
            why = f'<p class="why">{html.escape(b["why"])}</p>'
        elif b["is_filler"]:
            why = '<p class="owed">заливка без объяснения — почему сюда не нашлось фактуры?</p>'
        else:
            why = ""
        rows.append(
            f'<li>{thumb}<div>'
            f'<div class="meta"><span class="tc">{_tc(b["start"])}</span>'
            f'<span class="kind">{b["section"]}</span></div>'
            f'<p class="what">{html.escape(b["what"])}</p>{said}{why}'
            f'</div></li>'
        )
    return (
        f'<!doctype html><meta charset="utf-8">'
        f'<title>Контактный лист — {html.escape(project)}</title>'
        f'<style>{_CSS}</style>'
        f'<header><h1>Контактный лист — {html.escape(project)}</h1>'
        f'<p class="sub">{len(beats)} мест · один кандидат на место · '
        f'отметь то, что мимо — второй круг будет только по ним</p></header>'
        f'<ol>{"".join(rows)}</ol>'
    )


TOOL = ContactSheetTool()
