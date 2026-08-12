$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$initializer = Join-Path $root 'scripts\initialize-project.ps1'
if (-not (Test-Path -LiteralPath $initializer -PathType Leaf)) {
  throw 'Project initializer is missing'
}

$sandbox = Join-Path (Join-Path $PSScriptRoot 'fixtures') (".tmp-youtube-editorial-" + [guid]::NewGuid().ToString('N'))
try {
  & $initializer -ProjectRoot $sandbox -ProjectTitle 'Test video' -LegacySourceRoot 'C:\legacy\test-video'

  $requiredFiles = @(
    'PLAN.md',
    'preproduction\SCRIPT.md',
    'preproduction\REFERENCES.md',
    'preproduction\VISUAL-PACK.md',
    'preproduction\DESIGN.md'
  )
  $requiredDirectories = @(
    'preproduction\research', 'raw', 'assets', 'clips', 'transcripts',
    'compositions', 'previews', 'renders', 'youtube'
  )

  foreach ($relative in $requiredFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $sandbox $relative) -PathType Leaf)) {
      throw "Missing initialized file: $relative"
    }
  }
  foreach ($relative in $requiredDirectories) {
    if (-not (Test-Path -LiteralPath (Join-Path $sandbox $relative) -PathType Container)) {
      throw "Missing initialized directory: $relative"
    }
  }

  $planPath = Join-Path $sandbox 'PLAN.md'
  $plan = Get-Content -Raw -Encoding UTF8 $planPath
  if ($plan -notmatch 'Test video' -or $plan -notmatch [regex]::Escape('C:\legacy\test-video')) {
    throw 'PLAN.md does not record project identity and legacy source'
  }
  if (Test-Path -LiteralPath (Join-Path $sandbox 'canvas.json')) {
    throw 'canvas.json must remain optional'
  }

  $validator = Join-Path $root 'scripts\validate-script.ps1'
  $validationOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $validator -ProjectPath $sandbox -ExpectedStatus draft 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Initialized project failed script validation: $($validationOutput -join '; ')"
  }

  Set-Content -LiteralPath $planPath -Encoding UTF8 -NoNewline -Value 'SENTINEL'
  & $initializer -ProjectRoot $sandbox -ProjectTitle 'Changed title'
  if ((Get-Content -Raw -Encoding UTF8 $planPath) -ne 'SENTINEL') {
    throw 'Initializer overwrote an existing project file'
  }
} finally {
  if (Test-Path -LiteralPath $sandbox) {
    Remove-Item -LiteralPath $sandbox -Recurse -Force
  }
}

Write-Output 'PASS project initializer'
