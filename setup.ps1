# chatmonteur setup (Windows / PowerShell). Installs chatmonteur + the free local toolchain.
$ErrorActionPreference = "Stop"

function Say($m) { Write-Host "`n$m" -ForegroundColor Cyan }
function Have($c) { return [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Say "chatmonteur setup"

$miss = $false
if (-not (Have python))  { Write-Host "  ! python missing (need >=3.11)"; $miss = $true }
if (-not (Have ffmpeg))  { Write-Host "  ! ffmpeg missing  -> winget install Gyan.FFmpeg"; $miss = $true }
if (-not (Have ffprobe)) { Write-Host "  ! ffprobe missing (ships with ffmpeg)"; $miss = $true }
if (-not (Have npx))     { Write-Host "  - node/npx missing (only needed for motion/hyperframes)" }
if ($miss) { Write-Host "Install the items above, then re-run."; exit 1 }

Say "Installing chatmonteur + local transcription (faster-whisper) + auto-editor"
python -m pip install -e ".[whisper]"
python -m pip install auto-editor

if (-not (Test-Path config.toml)) { Copy-Item config.example.toml config.toml; Write-Host "  wrote config.toml" }
if (-not (Test-Path .env))        { Copy-Item .env.example .env;             Write-Host "  wrote .env" }

Say "Available hardware encoders"
ffmpeg -hide_banner -encoders 2>$null | Select-String -Pattern "nvenc|videotoolbox|qsv"

Say "Done. Try:  chatmonteur tools     then     chatmonteur edit your_video.mp4"
