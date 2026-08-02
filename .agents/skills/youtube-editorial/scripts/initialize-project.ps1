param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$ProjectTitle,
  [string]$LegacySourceRoot = ''
)

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$templateRoot = Join-Path $skillRoot 'assets\project-template'

if (-not (Test-Path -LiteralPath $templateRoot -PathType Container)) {
  throw "Project template is missing: $templateRoot"
}

$directories = @(
  '', 'preproduction', 'preproduction\research', 'raw', 'assets', 'clips',
  'transcripts', 'previews', 'renders', 'youtube'
)
foreach ($relative in $directories) {
  $path = if ($relative) { Join-Path $ProjectRoot $relative } else { $ProjectRoot }
  New-Item -ItemType Directory -Path $path -Force | Out-Null
}

Get-ChildItem -LiteralPath $templateRoot -File -Recurse | ForEach-Object {
  $relative = $_.FullName.Substring($templateRoot.Length).TrimStart('\', '/')
  $destination = Join-Path $ProjectRoot $relative
  if (Test-Path -LiteralPath $destination) { return }

  $parent = Split-Path -Parent $destination
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
  $content = Get-Content -Raw -Encoding UTF8 $_.FullName
  $content = $content.Replace('{{PROJECT_TITLE}}', $ProjectTitle)
  $content = $content.Replace('{{LEGACY_SOURCE_ROOT}}', $LegacySourceRoot)
  Set-Content -LiteralPath $destination -Encoding UTF8 -NoNewline -Value $content
}

Write-Output "PROJECT_READY $ProjectRoot"
