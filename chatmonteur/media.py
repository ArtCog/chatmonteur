"""Thin, well-behaved wrappers around ffmpeg / ffprobe.

Centralises the correctness rules that make "one command" trustworthy:
  * never stream-copy on a cut (always re-encode)
  * auto-detect a working hardware encoder, fall back to libx264
  * surface ffmpeg's real error tail instead of a generic crash
"""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable

from .core.errors import MissingDependencyError, ToolError

# Preference order for H.264 encoding. First one that ffmpeg actually has wins.
_H264_PREFERENCE = ("h264_nvenc", "h264_qsv", "h264_videotoolbox", "libx264")


def require(binary: str, *, hint: str | None = None) -> str:
    path = shutil.which(binary)
    if path is None:
        raise MissingDependencyError(binary, [f"binary:{binary}"], hint)
    return path


def run(
    cmd: list[str],
    *,
    log: Callable[[str], None] | None = None,
    desc: str | None = None,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a command, raising ToolError with the stderr tail on failure.

    ``cwd`` lets callers run ffmpeg from a directory so a filter can reference a
    file by bare name — the robust way to dodge Windows drive-colon parsing in
    ``subtitles=`` / ``lut3d=``.
    """
    if log and desc:
        log(desc)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd) if cwd else None,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or "").strip().splitlines()[-12:])
        raise ToolError(f"{cmd[0]} failed (exit {proc.returncode}):\n{tail}")
    return proc


@lru_cache(maxsize=1)
def _encoders() -> frozenset[str]:
    require("ffmpeg")
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        # format: " V....D h264_nvenc   NVIDIA ..."
        if len(parts) >= 2 and parts[0][:1] in ("V", "A") and parts[0] != "------":
            names.add(parts[1])
    return frozenset(names)


def has_encoder(name: str) -> bool:
    return name in _encoders()


def detect_encoder(preference: str = "auto") -> str:
    """Resolve config's encoder setting to a concrete, available encoder."""
    if preference != "auto":
        if has_encoder(preference):
            return preference
        # Asked for something missing — fall through to auto rather than fail late.
    for enc in _H264_PREFERENCE:
        if has_encoder(enc):
            return enc
    return "libx264"  # always present in any real ffmpeg build


def encoder_quality_args(encoder: str) -> list[str]:
    """Sensible quality-targeted args per encoder family (no bitrate guessing)."""
    if "nvenc" in encoder:
        return ["-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
    if "qsv" in encoder:
        return ["-global_quality", "23", "-preset", "medium"]
    if "videotoolbox" in encoder:
        return ["-q:v", "60"]
    return ["-preset", "medium", "-crf", "20"]  # libx264


def filter_path(path: str | Path) -> str:
    """Escape a path for use *inside* an ffmpeg filter (subtitles=, lut3d=).

    On Windows the drive colon and backslashes break filter parsing; convert to
    forward slashes and escape the colon: ``C:\\a\\b.srt`` -> ``C\\:/a/b.srt``.
    """
    s = str(path).replace("\\", "/")
    return s.replace(":", "\\:")


def ffprobe_json(path: str | Path) -> dict:
    require("ffprobe")
    proc = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    return json.loads(proc.stdout or "{}")


def source_fps(path: str | Path, default: float = 60.0) -> float:
    """Average frame rate of the first video stream, as a float."""
    info = ffprobe_json(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/0"
            num, _, den = rate.partition("/")
            try:
                n, d = float(num), float(den or 1)
                if d and n:
                    return round(n / d, 3)
            except ValueError:
                pass
    return default


def mean_volume_db(path: str | Path) -> float | None:
    """Measured mean volume (dBFS) via ffmpeg volumedetect.

    Used to verify audio by LEVEL, not by track duration — a track of the right
    length can still be silence.
    """
    require("ffmpeg")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].strip().split()[0])
            except (IndexError, ValueError):
                return None
    return None
