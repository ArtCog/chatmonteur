param(
  [Parameter(Mandatory = $true)][string]$SkillRoot,
  [switch]$AllowPlannedMissingModules
)

$ErrorActionPreference = 'Stop'
$resolved = (Resolve-Path -LiteralPath $SkillRoot).Path
$skillPath = Join-Path $resolved 'SKILL.md'
$errors = [System.Collections.Generic.List[string]]::new()
$plannedMissingModules = @(
  'references/05-artur-voice.md',
  'references/06-spoken-audit.md',
  'references/07-russian-edit.md',
  'references/08-retention-evidence.md',
  'references/09-human-approval.md',
  'references/10-production-handoff.md'
)

if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) {
  $errors.Add('SKILL.md is missing')
} else {
  $content = Get-Content -Raw -Encoding UTF8 $skillPath
  if ($content -notmatch '(?ms)^---\s*.*?^name:\s*youtube-editorial\s*$.*?^description:\s*\S.+?^---\s*$') {
    $errors.Add('frontmatter must contain name youtube-editorial and a non-empty description')
  }
  $matches = [regex]::Matches($content, '(?:references|templates|profiles|scripts)/[A-Za-z0-9._/-]+')
  foreach ($match in $matches) {
    $target = Join-Path $resolved ($match.Value -replace '/', '\')
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
      if ($AllowPlannedMissingModules -and $plannedMissingModules -contains $match.Value) {
        continue
      }
      $errors.Add("referenced file is missing: $($match.Value)")
    }
  }
}

if ($errors.Count -gt 0) {
  $errors | ForEach-Object { Write-Output "ERROR $_" }
  exit 1
}

Write-Output "PACKAGE_OK $resolved"
exit 0
