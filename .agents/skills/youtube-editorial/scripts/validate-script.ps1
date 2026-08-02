param(
  [Parameter(Mandatory=$true)][string]$ProjectPath,
  [string]$ExpectedStatus
)
$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()

try { $resolved = (Resolve-Path -LiteralPath $ProjectPath).Path } catch {
  Write-Output "ERROR project path does not exist: $ProjectPath"; exit 1
}
$skillRoot = Split-Path -Parent $PSScriptRoot
$fixturesRoot = Join-Path $skillRoot 'tests\fixtures'
$videoRoot = 'C:\Projects\Video'
$chatcutRoot = (Resolve-Path -LiteralPath (Join-Path $skillRoot '..\..\..')).Path
$chatcutProjectsRoot = Join-Path $chatcutRoot 'projects'
$underFixtures = $resolved.StartsWith($fixturesRoot, [System.StringComparison]::OrdinalIgnoreCase)
$underVideo = $resolved.StartsWith($videoRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
$underChatcut = $resolved.StartsWith($chatcutProjectsRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
if (-not ($underFixtures -or $underVideo -or $underChatcut)) { $errors.Add('project path must be under ChatMonteur projects, C:\Projects\Video, or skill test fixtures') }

$preproductionRoot = Join-Path $resolved 'preproduction'
$newScriptPath = Join-Path $preproductionRoot 'SCRIPT.md'
$usesNewContract = Test-Path -LiteralPath $newScriptPath -PathType Leaf
$scriptPath = if ($usesNewContract) { $newScriptPath } else { Join-Path $resolved 'SCRIPT.md' }
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
  $errors.Add('SCRIPT.md is missing from the project root or preproduction directory')
} else {
  $script = Get-Content -Raw -Encoding UTF8 $scriptPath
  $statusMatch = [regex]::Match($script, '(?m)^editorial_status:\s*([^\r\n]+)')
  $status = if ($statusMatch.Success) { $statusMatch.Groups[1].Value.Trim() } else { '' }
  $allowed = @('draft','structure_review','editorial_review','human_review_required','approved_by_artur')
  if ($status -notin $allowed) { $errors.Add("unknown editorial_status: $status") }
  if ($ExpectedStatus -and $status -ne $ExpectedStatus) { $errors.Add("expected status $ExpectedStatus but found $status") }
  if ($status -eq 'approved_by_artur' -and $script -notmatch '(?m)^approved_by:\s*Artur\s*$') { $errors.Add('approved_by_artur requires approved_by: Artur') }
  $body = [regex]::Replace($script, '(?s)\A---.*?---\s*', '')
  if ($body -match '(?mi)^#{1,6}\s*(script audit|production notes|visual pack)\b|^\s*\[(?:B-?ROLL|CUT|SOURCE):') {
    $errors.Add('SCRIPT.md body contains audit or production cue blocks')
  }
  $requiredFiles = if ($usesNewContract) {
    @(
      (Join-Path $resolved 'PLAN.md'),
      (Join-Path $preproductionRoot 'REFERENCES.md')
    )
  } else {
    @(
      (Join-Path $resolved 'SCRIPT-NOTES.md'),
      (Join-Path $resolved 'SCRIPT-AUDIT.md'),
      (Join-Path $resolved 'REFERENCES.md')
    )
  }
  foreach ($requiredPath in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) { $errors.Add("required editorial file is missing: $requiredPath") }
  }
  if ($status -eq 'approved_by_artur') {
    $handoffRoot = if ($usesNewContract) { $preproductionRoot } else { $resolved }
    foreach ($name in @('VISUAL-PACK.md','DESIGN.md')) {
      if (-not (Test-Path -LiteralPath (Join-Path $handoffRoot $name) -PathType Leaf)) { $errors.Add("$name is missing for production handoff") }
    }
  }
  $notesPath = if ($usesNewContract) { Join-Path $resolved 'PLAN.md' } else { Join-Path $resolved 'SCRIPT-NOTES.md' }
  $refsPath = if ($usesNewContract) { Join-Path $preproductionRoot 'REFERENCES.md' } else { Join-Path $resolved 'REFERENCES.md' }
  if ((Test-Path $notesPath) -and (Test-Path $refsPath)) {
    $notes = Get-Content -Raw -Encoding UTF8 $notesPath
    $refs = Get-Content -Raw -Encoding UTF8 $refsPath
    $ids = [regex]::Matches($notes, '\[SOURCE:([A-Za-z0-9_-]+)\]') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
    foreach ($id in $ids) { if ($refs -notmatch "(?m)^\s*(?:source_id:\s*|##\s*)$([regex]::Escape($id))\b") { $errors.Add("source ID missing from REFERENCES.md: $id") } }
  }
}

if ($errors.Count) { $errors | ForEach-Object { Write-Output "ERROR $_" }; exit 1 }
Write-Output "SCRIPT_OK $resolved"
exit 0
