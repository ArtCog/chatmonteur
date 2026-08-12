#!/usr/bin/env bash
# chatmonteur setup (macOS / Linux). Installs chatmonteur + the free local toolchain.
set -euo pipefail

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

say "chatmonteur setup"

# --- prerequisites (not auto-installed; report clearly) ---
miss=0
have python3 || { echo "  ! python3 missing (need >=3.11)"; miss=1; }
have ffmpeg  || { echo "  ! ffmpeg missing  → brew install ffmpeg  /  apt install ffmpeg"; miss=1; }
have ffprobe || { echo "  ! ffprobe missing (ships with ffmpeg)"; miss=1; }
have node    || echo "  - node missing (only needed for motion/hyperframes)"
[ "$miss" = 1 ] && { echo "Install the items above, then re-run."; exit 1; }

# --- python deps ---
say "Installing chatmonteur + local transcription + image support + auto-editor"
python3 -m pip install -e ".[whisper,emoji]"
python3 -m pip install auto-editor

# --- config scaffolding ---
[ -f config.toml ] || cp config.example.toml config.toml && echo "  wrote config.toml"
[ -f .env ] || cp .env.example .env && echo "  wrote .env"

# --- repository safety ---
if git rev-parse --git-dir >/dev/null 2>&1; then
  git config core.hooksPath .githooks
  echo "  enabled repository safety hooks"
fi

# --- report encoders ---
say "Available hardware encoders"
ffmpeg -hide_banner -encoders 2>/dev/null | grep -iE 'nvenc|videotoolbox|qsv' || echo "  none — will use libx264 (CPU)"

say "Done. Try:  chatmonteur tools     then     chatmonteur edit your_video.mp4"
