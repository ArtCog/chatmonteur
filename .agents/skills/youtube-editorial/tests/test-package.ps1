$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$validator = Join-Path $root 'scripts\validate-package.ps1'
$validFixture = Join-Path $PSScriptRoot 'fixtures\package-valid'
$invalidFixture = Join-Path $PSScriptRoot 'fixtures\package-invalid'
$stagedFixture = Join-Path $PSScriptRoot 'fixtures\package-staged'
$unexpectedStagedFixture = Join-Path $stagedFixture 'unexpected'

$validOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $validFixture
if ($LASTEXITCODE -ne 0) { throw "Expected valid fixture to succeed; exit code: $LASTEXITCODE" }
if (($validOutput | Out-String) -notmatch 'PACKAGE_OK') { throw 'Expected valid fixture to print PACKAGE_OK' }

$invalidOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $invalidFixture
if ($LASTEXITCODE -eq 0) { throw 'Expected invalid fixture to fail' }
if (($invalidOutput | Out-String) -notmatch 'ERROR referenced file is missing: references/missing\.md') {
  throw 'Expected invalid fixture to report its missing reference'
}

$strictStagedOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $stagedFixture
if ($LASTEXITCODE -eq 0) { throw 'Expected strict staged-fixture validation to fail' }
foreach ($path in @(
  'references/05-artur-voice.md',
  'references/06-spoken-audit.md',
  'references/07-russian-edit.md',
  'references/08-retention-evidence.md',
  'references/09-human-approval.md',
  'references/10-production-handoff.md'
)) {
  if (($strictStagedOutput | Out-String) -notmatch [regex]::Escape("ERROR referenced file is missing: $path")) {
    throw "Expected strict staged-fixture validation to report: $path"
  }
}

$stagedFailures = [System.Collections.Generic.List[string]]::new()
$allowedStagedOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $stagedFixture -AllowPlannedMissingModules
if ($LASTEXITCODE -ne 0 -or ($allowedStagedOutput | Out-String) -notmatch 'PACKAGE_OK') {
  $stagedFailures.Add('Expected staged-fixture validation to tolerate the six planned missing modules')
}

$stagedLiveOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $root -AllowPlannedMissingModules
if ($LASTEXITCODE -ne 0 -or ($stagedLiveOutput | Out-String) -notmatch 'PACKAGE_OK') {
  $stagedFailures.Add('Expected staged live-package validation to succeed')
}

$unexpectedStagedOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -SkillRoot $unexpectedStagedFixture -AllowPlannedMissingModules
if ($LASTEXITCODE -eq 0) {
  $stagedFailures.Add('Expected staged validation to reject an unexpected missing reference')
}
if (($unexpectedStagedOutput | Out-String) -notmatch 'ERROR referenced file is missing: references/missing\.md') {
  $stagedFailures.Add('Expected staged validation to report the unexpected missing reference')
}

if ($stagedFailures.Count -gt 0) {
  throw ($stagedFailures -join [Environment]::NewLine)
}

Write-Output 'PASS package validator'
