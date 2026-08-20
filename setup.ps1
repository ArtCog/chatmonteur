# chatmonteur setup (Windows / PowerShell). Installs chatmonteur + the free local toolchain.
$ErrorActionPreference = "Stop"

function Say($m) { Write-Host "`n$m" -ForegroundColor Cyan }
function Have($c) { return [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Push-Location -LiteralPath $PSScriptRoot
try {
    Say "chatmonteur setup"

    $miss = $false
    if (-not (Have python))  { Write-Host "  ! python missing (need >=3.11)"; $miss = $true }
    if (-not (Have ffmpeg))  { Write-Host "  ! ffmpeg missing  -> winget install Gyan.FFmpeg"; $miss = $true }
    if (-not (Have ffprobe)) { Write-Host "  ! ffprobe missing (ships with ffmpeg)"; $miss = $true }
    if (-not (Have npx))     { Write-Host "  - node/npx missing (only needed for motion/hyperframes)" }
    if ($miss) { throw "Install the items above, then re-run." }

    Say "Installing chatmonteur + local transcription + image support + auto-editor"
    python -m pip install -e ".[whisper,emoji]"
    if ($LASTEXITCODE -ne 0) { throw "chatmonteur dependency installation failed (exit $LASTEXITCODE)" }
    python -m pip install auto-editor
    if ($LASTEXITCODE -ne 0) { throw "auto-editor installation failed (exit $LASTEXITCODE)" }

    if (-not (Test-Path config.toml)) { Copy-Item config.example.toml config.toml; Write-Host "  wrote config.toml" }
    if (-not (Test-Path .env))        { Copy-Item .env.example .env;             Write-Host "  wrote .env" }

    if ((Have git) -and (Test-Path .git)) {
        git config core.hooksPath .githooks
        Write-Host "  enabled repository safety hooks"
    }

    Say "Available hardware encoders"
    ffmpeg -hide_banner -encoders 2>$null | Select-String -Pattern "nvenc|videotoolbox|qsv"

    Say "Done. Try:  chatmonteur tools     then     chatmonteur edit your_video.mp4"
}
finally {
    Pop-Location
}
