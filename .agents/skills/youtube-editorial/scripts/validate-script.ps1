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
$underFixtures = $resolved.StartsWith($fixturesRoot, [System.StringComparison]::OrdinalIgnoreCase)
$underVideo = $resolved.StartsWith($videoRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
if (-not ($underFixtures -or $underVideo)) { $errors.Add('project path must be under C:\Projects\Video or skill test fixtures') }

$scriptPath = Join-Path $resolved 'SCRIPT.md'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
  $errors.Add('SCRIPT.md is missing')
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
  foreach ($name in @('SCRIPT-NOTES.md','SCRIPT-AUDIT.md','REFERENCES.md')) {
    if (-not (Test-Path -LiteralPath (Join-Path $resolved $name) -PathType Leaf)) { $errors.Add("$name is missing") }
  }
  if ($status -eq 'approved_by_artur') {
    foreach ($name in @('VISUAL-PACK.md','DESIGN.md')) {
      if (-not (Test-Path -LiteralPath (Join-Path $resolved $name) -PathType Leaf)) { $errors.Add("$name is missing for production handoff") }
    }
  }
  $notesPath = Join-Path $resolved 'SCRIPT-NOTES.md'
  $refsPath = Join-Path $resolved 'REFERENCES.md'
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

