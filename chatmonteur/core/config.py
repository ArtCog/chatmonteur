"""Configuration: opinionated defaults, overridable via ``config.toml``,
secrets read from the environment / ``.env`` (never committed).

Defaults are tuned for the talking-head pipeline and bias to the *free*,
cross-platform path (local whisper, auto-detected encoder).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from .errors import ConfigError


@dataclass(frozen=True)
class TranscribeConfig:
    backend: str = "faster-whisper"  # "faster-whisper" (free, local) | "elevenlabs" (paid)
    model: str = "large-v3"
    language: str | None = None  # None = autodetect


@dataclass(frozen=True)
class EncodeConfig:
    # "auto" picks the best available hardware encoder, else libx264. Never -c copy.
    encoder: str = "auto"  # auto | h264_nvenc | libx264 | h264_videotoolbox | h264_qsv
    final_height: int = 1440
    fps: int = 60
    # Loudness target (EBU R128) — applied as the LAST audio step.
    loudness_lufs: float = -14.0


@dataclass(frozen=True)
class Config:
    root: Path
    transcribe: TranscribeConfig = field(default_factory=TranscribeConfig)
    encode: EncodeConfig = field(default_factory=EncodeConfig)

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"

    def get_secret(self, name: str) -> str | None:
        """Resolve a secret from the process env first, then ``.env``.

        Secrets are never stored in Config or logged — only fetched on demand.
        """
        if name in os.environ:
            return os.environ[name]
        return _read_dotenv(self.root / ".env").get(name)


def load_config(root: str | Path) -> Config:
    """Load ``<root>/config.toml`` over the built-in defaults.

    Unknown keys are ignored (forward-compatible); wrong *types* raise
    ConfigError so a typo doesn't silently change behaviour.
    """
    root = Path(root).resolve()
    cfg = Config(root=root)

    toml_path = root / "config.toml"
    if not toml_path.exists():
        return cfg

    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"could not read {toml_path}: {exc}") from exc

    try:
        if "transcribe" in data:
            cfg = replace(cfg, transcribe=replace(cfg.transcribe, **_known(TranscribeConfig, data["transcribe"])))
        if "encode" in data:
            cfg = replace(cfg, encode=replace(cfg.encode, **_known(EncodeConfig, data["encode"])))
    except TypeError as exc:
        raise ConfigError(f"invalid value in {toml_path}: {exc}") from exc

    return cfg


def _known(dc_type: type, raw: dict) -> dict:
    """Keep only keys that exist on the dataclass — ignore unknown, forward-compatibly."""
    allowed = {f.name for f in dc_type.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return {k: v for k, v in raw.items() if k in allowed}


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal ``.env`` parser (no dependency). Lines like ``KEY=value``;
    blank lines and ``#`` comments ignored. Values are not unquoted-magically."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out
