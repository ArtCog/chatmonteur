$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$validator = Join-Path $root 'scripts\validate-script.ps1'
$valid = Join-Path $PSScriptRoot 'fixtures\valid-project'
$invalid = Join-Path $PSScriptRoot 'fixtures\invalid-approved-project'

$before = Get-ChildItem -Recurse -File (Join-Path $PSScriptRoot 'fixtures') | ForEach-Object { "$($_.FullName)|$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" }
$validOutput = & $validator -ProjectPath $valid -ExpectedStatus human_review_required 2>&1
if ($LASTEXITCODE -ne 0 -or ($validOutput -join "`n") -notmatch 'SCRIPT_OK') { throw "valid project rejected: $validOutput" }
$invalidOutput = & $validator -ProjectPath $invalid 2>&1
if ($LASTEXITCODE -eq 0 -or ($invalidOutput -join "`n") -notmatch 'approved_by_artur requires approved_by: Artur') { throw "invalid approval was not rejected: $invalidOutput" }
$after = Get-ChildItem -Recurse -File (Join-Path $PSScriptRoot 'fixtures') | ForEach-Object { "$($_.FullName)|$((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" }
if ((Compare-Object $before $after)) { throw 'validator modified fixtures' }
Write-Output 'PASS script validator'

