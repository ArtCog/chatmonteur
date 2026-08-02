$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$skillPath = Join-Path $root 'SKILL.md'
$intakePath = Join-Path $root 'references\01-intake.md'
$evidencePath = Join-Path $root 'references\03-evidence-pack.md'
$voiceModulePath = Join-Path $root 'references\05-artur-voice.md'
$voiceProfilePath = Join-Path $root 'profiles\artur-voice.md'
$voiceSourcesPath = Join-Path $root 'profiles\artur-voice-sources.md'
$validVoiceFixturePath = Join-Path $PSScriptRoot 'fixtures\voice-profile-valid.md'
$invalidVoiceFixturePath = Join-Path $PSScriptRoot 'fixtures\voice-profile-invalid.md'

function Get-YamlPayload {
  param([Parameter(Mandatory = $true)][string]$Content)

  $fence = [regex]::Match($Content, '(?ms)^```ya?ml[ \t]*\r?\n(?<yaml>.*?)^```[ \t]*$')
  if ($fence.Success) { return $fence.Groups['yaml'].Value }
  return $Content
}

function Get-YamlSection {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyString()][string[]]$Lines,
    [Parameter(Mandatory = $true)][string]$Key
  )

  $pattern = '^' + [regex]::Escape($Key) + ':[ \t]*(?<inline>.*)$'
  for ($index = 0; $index -lt $Lines.Count; $index++) {
    $match = [regex]::Match($Lines[$index], $pattern)
    if (-not $match.Success) { continue }

    $indent = 0
    $end = $Lines.Count
    for ($cursor = $index + 1; $cursor -lt $Lines.Count; $cursor++) {
      if ([string]::IsNullOrWhiteSpace($Lines[$cursor]) -or $Lines[$cursor].TrimStart().StartsWith('#')) { continue }
      $nextIndent = ([regex]::Match($Lines[$cursor], '^ *')).Value.Length
      if ($nextIndent -le $indent) {
        $end = $cursor
        break
      }
    }

    $body = if ($end -gt ($index + 1)) { @($Lines[($index + 1)..($end - 1)]) } else { @() }
    return [pscustomobject]@{
      Found       = $true
      Indent      = $indent
      InlineValue = $match.Groups['inline'].Value.Trim()
      Lines       = $body
    }
  }

  return [pscustomobject]@{ Found = $false; Indent = -1; InlineValue = ''; Lines = @() }
}

function Remove-YamlInlineComment {
  param([AllowEmptyString()][string]$Value)

  $inSingleQuote = $false
  $inDoubleQuote = $false
  $escaped = $false
  for ($index = 0; $index -lt $Value.Length; $index++) {
    $character = $Value[$index]
    if ($inDoubleQuote) {
      if ($escaped) { $escaped = $false; continue }
      if ($character -eq '\') { $escaped = $true; continue }
      if ($character -eq '"') { $inDoubleQuote = $false }
      continue
    }
    if ($inSingleQuote) {
      if ($character -eq "'") {
        if ($index + 1 -lt $Value.Length -and $Value[$index + 1] -eq "'") { $index++; continue }
        $inSingleQuote = $false
      }
      continue
    }

    $canStartQuote = $index -eq 0 -or [char]::IsWhiteSpace($Value[$index - 1]) -or $Value[$index - 1] -in @(':', ',', '[', '{')
    if ($character -eq '"' -and $canStartQuote) { $inDoubleQuote = $true; continue }
    if ($character -eq "'" -and $canStartQuote) { $inSingleQuote = $true; continue }
    if ($character -eq '#' -and ($index -eq 0 -or [char]::IsWhiteSpace($Value[$index - 1]))) {
      return $Value.Substring(0, $index).TrimEnd()
    }
  }
  return $Value.TrimEnd()
}

function Get-YamlScalarResult {
  param(
    [AllowNull()]$RawValue,
    [AllowEmptyCollection()][string[]]$Lines = @(),
    [int]$ValueLineIndex = -1,
    [int]$ParentIndent = -1
  )

  $invalid = [pscustomobject]@{ IsScalar = $false; IsNonEmpty = $false; Value = ''; IsBlock = $false }
  if ($null -eq $RawValue) { return $invalid }
  $raw = (Remove-YamlInlineComment ([string]$RawValue)).Trim()
  if (-not $raw) {
    return [pscustomobject]@{ IsScalar = $true; IsNonEmpty = $false; Value = ''; IsBlock = $false }
  }

  if ($raw -match '^[|>]') {
    if ($raw -notmatch '^(?<style>[|>])(?:[+-]?[1-9]?|[1-9][+-]?)?$' -or $ValueLineIndex -lt 0 -or $ParentIndent -lt 0) {
      return $invalid
    }
    $blockStyle = $Matches['style']
    $blockLines = [System.Collections.Generic.List[string]]::new()
    for ($lineIndex = $ValueLineIndex + 1; $lineIndex -lt $Lines.Count; $lineIndex++) {
      $line = $Lines[$lineIndex]
      if ([string]::IsNullOrWhiteSpace($line)) { $blockLines.Add(''); continue }
      $indent = ([regex]::Match($line, '^ *')).Value.Length
      if ($indent -le $ParentIndent) { break }
      $blockLines.Add($line)
    }
    $contentLines = @($blockLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($contentLines.Count -eq 0) {
      return [pscustomobject]@{ IsScalar = $true; IsNonEmpty = $false; Value = ''; IsBlock = $true }
    }
    $contentIndent = ($contentLines | ForEach-Object { ([regex]::Match($_, '^ *')).Value.Length } | Measure-Object -Minimum).Minimum
    $normalizedLines = @($blockLines | ForEach-Object {
      if ([string]::IsNullOrWhiteSpace($_)) { '' } else { $_.Substring([Math]::Min($contentIndent, $_.Length)) }
    })
    $value = if ($blockStyle -eq '>') { ($normalizedLines -join ' ').Trim() } else { ($normalizedLines -join "`n").Trim() }
    return [pscustomobject]@{ IsScalar = $true; IsNonEmpty = -not [string]::IsNullOrWhiteSpace($value); Value = $value; IsBlock = $true }
  }

  if ($raw.StartsWith('[') -or $raw.StartsWith('{')) { return $invalid }
  if ($raw -match '^(?i:null|~)$') {
    return [pscustomobject]@{ IsScalar = $true; IsNonEmpty = $false; Value = ''; IsBlock = $false }
  }

  $value = $raw
  if ($raw.StartsWith('"')) {
    if ($raw.Length -lt 2 -or -not $raw.EndsWith('"')) { return $invalid }
    $value = $raw.Substring(1, $raw.Length - 2)
  } elseif ($raw.StartsWith("'")) {
    if ($raw.Length -lt 2 -or -not $raw.EndsWith("'")) { return $invalid }
    $value = $raw.Substring(1, $raw.Length - 2).Replace("''", "'")
  }
  return [pscustomobject]@{
    IsScalar   = $true
    IsNonEmpty = -not [string]::IsNullOrWhiteSpace($value)
    Value      = $value
    IsBlock    = $false
  }
}

function Get-UnquotedValue {
  param([AllowEmptyString()][string]$Value)

  $trimmed = $Value.Trim()
  if ($trimmed.Length -ge 2) {
    $first = $trimmed.Substring(0, 1)
    $last = $trimmed.Substring($trimmed.Length - 1, 1)
    if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
      return $trimmed.Substring(1, $trimmed.Length - 2)
    }
  }
  return $trimmed
}

function Get-YamlRecordFieldScalarResult {
  param(
    [Parameter(Mandatory = $true)]$Record,
    [Parameter(Mandatory = $true)][string]$FieldName
  )

  if (-not $Record.Fields.ContainsKey($FieldName)) { return Get-YamlScalarResult -RawValue $null }
  $field = $Record.Fields[$FieldName]
  return Get-YamlScalarResult -RawValue $field.Value -Lines $Record.Lines -ValueLineIndex $field.Index -ParentIndent $field.Indent
}

function Split-YamlFlowTopLevel {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text,
    [Parameter(Mandatory = $true)][char]$Delimiter,
    [int]$MaxParts = 0
  )

  $parts = [System.Collections.Generic.List[string]]::new()
  $start = 0
  $braceDepth = 0
  $bracketDepth = 0
  $inSingleQuote = $false
  $inDoubleQuote = $false
  $escaped = $false
  for ($index = 0; $index -lt $Text.Length; $index++) {
    $character = $Text[$index]
    if ($inDoubleQuote) {
      if ($escaped) { $escaped = $false; continue }
      if ($character -eq '\') { $escaped = $true; continue }
      if ($character -eq '"') { $inDoubleQuote = $false }
      continue
    }
    if ($inSingleQuote) {
      if ($character -eq "'") {
        if ($index + 1 -lt $Text.Length -and $Text[$index + 1] -eq "'") { $index++; continue }
        $inSingleQuote = $false
      }
      continue
    }

    $canStartQuote = $index -eq 0 -or [char]::IsWhiteSpace($Text[$index - 1]) -or $Text[$index - 1] -in @(':', ',', '[', '{')
    if ($character -eq '"' -and $canStartQuote) { $inDoubleQuote = $true; continue }
    if ($character -eq "'" -and $canStartQuote) { $inSingleQuote = $true; continue }
    if ($character -eq '{') { $braceDepth++; continue }
    if ($character -eq '}') { $braceDepth--; if ($braceDepth -lt 0) { return [pscustomobject]@{ IsValid = $false; Parts = @() } }; continue }
    if ($character -eq '[') { $bracketDepth++; continue }
    if ($character -eq ']') { $bracketDepth--; if ($bracketDepth -lt 0) { return [pscustomobject]@{ IsValid = $false; Parts = @() } }; continue }
    if ($character -eq $Delimiter -and $braceDepth -eq 0 -and $bracketDepth -eq 0 -and ($MaxParts -le 0 -or $parts.Count -lt ($MaxParts - 1))) {
      $parts.Add($Text.Substring($start, $index - $start).Trim())
      $start = $index + 1
    }
  }
  if ($inSingleQuote -or $inDoubleQuote -or $braceDepth -ne 0 -or $bracketDepth -ne 0) {
    return [pscustomobject]@{ IsValid = $false; Parts = @() }
  }
  $parts.Add($Text.Substring($start).Trim())
  return [pscustomobject]@{ IsValid = $true; Parts = $parts.ToArray() }
}

function Get-YamlInlineMapResult {
  param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$RawValue)

  $text = (Remove-YamlInlineComment $RawValue).Trim()
  if (-not $text.StartsWith('{')) { return [pscustomobject]@{ IsMap = $false; IsValid = $false; Fields = @{} } }
  if ($text.Length -lt 2 -or -not $text.EndsWith('}')) { return [pscustomobject]@{ IsMap = $true; IsValid = $false; Fields = @{} } }
  $inner = $text.Substring(1, $text.Length - 2).Trim()
  if (-not $inner) { return [pscustomobject]@{ IsMap = $true; IsValid = $true; Fields = @{} } }

  $entries = Split-YamlFlowTopLevel -Text $inner -Delimiter ','
  if (-not $entries.IsValid) { return [pscustomobject]@{ IsMap = $true; IsValid = $false; Fields = @{} } }
  $fields = @{}
  foreach ($entry in $entries.Parts) {
    $pair = Split-YamlFlowTopLevel -Text $entry -Delimiter ':' -MaxParts 2
    if (-not $pair.IsValid -or $pair.Parts.Count -ne 2) {
      return [pscustomobject]@{ IsMap = $true; IsValid = $false; Fields = @{} }
    }
    $keyResult = Get-YamlScalarResult -RawValue $pair.Parts[0]
    if (-not $keyResult.IsNonEmpty -or $fields.ContainsKey($keyResult.Value)) {
      return [pscustomobject]@{ IsMap = $true; IsValid = $false; Fields = @{} }
    }
    $fields[$keyResult.Value] = $pair.Parts[1]
  }
  return [pscustomobject]@{ IsMap = $true; IsValid = $true; Fields = $fields }
}

function Test-VoiceTimestamp {
  param([Parameter(Mandatory = $true)][string]$Value)

  if ($Value -notmatch '^\d{2}:\d{2}(?::\d{2})?$') { return $false }
  $parts = @($Value -split ':')
  if ([int]$parts[-1] -gt 59) { return $false }
  if ($parts.Count -eq 3 -and [int]$parts[1] -gt 59) { return $false }
  return $true
}

function Get-YamlListRecords {
  param(
    [Parameter(Mandatory = $true)]$Section,
    [Parameter(Mandatory = $true)][string]$IdKey
  )

  $records = [System.Collections.Generic.List[object]]::new()
  $unparsed = 0
  $bodyHasContent = @($Section.Lines | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_) -and -not $_.TrimStart().StartsWith('#')
  }).Count -gt 0

  if ($Section.InlineValue -and $Section.InlineValue -ne '[]') { $unparsed++ }
  if ($Section.InlineValue -eq '[]' -and $bodyHasContent) { $unparsed++ }

  $listItems = [System.Collections.Generic.List[object]]::new()
  for ($index = 0; $index -lt $Section.Lines.Count; $index++) {
    $match = [regex]::Match($Section.Lines[$index], '^(?<indent> *)-\s+')
    if ($match.Success) {
      $listItems.Add([pscustomobject]@{ Index = $index; Indent = $match.Groups['indent'].Value.Length })
    }
  }

  if ($listItems.Count -eq 0) {
    if ($bodyHasContent) { $unparsed++ }
    return [pscustomobject]@{ Records = @(); UnparsedCount = $unparsed; BodyHasContent = $bodyHasContent }
  }

  $recordIndent = ($listItems | Measure-Object -Property Indent -Minimum).Minimum
  $topItems = @($listItems | Where-Object { $_.Indent -eq $recordIndent })
  for ($itemNumber = 0; $itemNumber -lt $topItems.Count; $itemNumber++) {
    $start = $topItems[$itemNumber].Index
    $end = if ($itemNumber + 1 -lt $topItems.Count) { $topItems[$itemNumber + 1].Index } else { $Section.Lines.Count }
    $idPattern = '^(?<indent> *)-\s+' + [regex]::Escape($IdKey) + ':[ \t]*(?<id>.+?)[ \t]*$'
    $idMatch = [regex]::Match($Section.Lines[$start], $idPattern)
    if (-not $idMatch.Success) {
      $unparsed++
      continue
    }

    $block = @($Section.Lines[$start..($end - 1)])
    $fieldCandidates = [System.Collections.Generic.List[object]]::new()
    for ($blockIndex = 1; $blockIndex -lt $block.Count; $blockIndex++) {
      $fieldMatch = [regex]::Match($block[$blockIndex], '^(?<indent> +)(?<key>[A-Za-z_][A-Za-z0-9_]*):[ \t]*(?<value>.*)$')
      if ($fieldMatch.Success -and $fieldMatch.Groups['indent'].Value.Length -gt $recordIndent) {
        $fieldCandidates.Add([pscustomobject]@{
          Index  = $blockIndex
          Indent = $fieldMatch.Groups['indent'].Value.Length
          Key    = $fieldMatch.Groups['key'].Value
          Value  = $fieldMatch.Groups['value'].Value.Trim()
        })
      }
    }

    $fields = @{}
    if ($fieldCandidates.Count -gt 0) {
      $fieldIndent = ($fieldCandidates | Measure-Object -Property Indent -Minimum).Minimum
      foreach ($field in @($fieldCandidates | Where-Object { $_.Indent -eq $fieldIndent })) {
        $fields[$field.Key] = $field
      }
    }

    $rawId = $idMatch.Groups['id'].Value.Trim()
    $idScalar = Get-YamlScalarResult -RawValue $rawId -Lines $block -ValueLineIndex 0 -ParentIndent ($recordIndent + 2)
    $records.Add([pscustomobject]@{
      Id         = $idScalar.Value
      IdScalar   = $idScalar
      RawId      = $rawId
      ItemIndent = $recordIndent
      Lines      = $block
      Fields     = $fields
    })
  }

  return [pscustomobject]@{ Records = $records.ToArray(); UnparsedCount = $unparsed; BodyHasContent = $bodyHasContent }
}

function Test-ProvisionalObservationSection {
  param([Parameter(Mandatory = $true)]$Section)

  if (-not $Section.Found -or $Section.InlineValue) { return $false }
  $listItems = [System.Collections.Generic.List[object]]::new()
  for ($index = 0; $index -lt $Section.Lines.Count; $index++) {
    $match = [regex]::Match($Section.Lines[$index], '^(?<indent> *)-\s*(?<value>.*)$')
    if ($match.Success) {
      $listItems.Add([pscustomobject]@{
        Index  = $index
        Indent = $match.Groups['indent'].Value.Length
        Value  = $match.Groups['value'].Value.Trim()
      })
    }
  }
  if ($listItems.Count -eq 0) { return $false }

  $itemIndent = ($listItems | Measure-Object -Property Indent -Minimum).Minimum
  $topItems = @($listItems | Where-Object { $_.Indent -eq $itemIndent })
  for ($itemNumber = 0; $itemNumber -lt $topItems.Count; $itemNumber++) {
    $item = $topItems[$itemNumber]
    $end = if ($itemNumber + 1 -lt $topItems.Count) { $topItems[$itemNumber + 1].Index } else { $Section.Lines.Count }
    if ($item.Value -match '^observation:[ \t]*(?<value>.*)$') {
      $observationScalar = Get-YamlScalarResult -RawValue $Matches['value'] -Lines $Section.Lines -ValueLineIndex $item.Index -ParentIndent ($itemIndent + 2)
      if ($observationScalar.IsNonEmpty) { return $true }
      continue
    }
    if ($item.Value -match '^observation_id:') {
      $fieldCandidates = [System.Collections.Generic.List[object]]::new()
      for ($cursor = $item.Index + 1; $cursor -lt $end; $cursor++) {
        $field = [regex]::Match($Section.Lines[$cursor], '^(?<indent> +)(?<key>[A-Za-z_][A-Za-z0-9_]*):[ \t]*(?<value>.*)$')
        if ($field.Success -and $field.Groups['indent'].Value.Length -gt $itemIndent) {
          $fieldCandidates.Add([pscustomobject]@{
            Index  = $cursor
            Indent = $field.Groups['indent'].Value.Length
            Key    = $field.Groups['key'].Value
            Value  = $field.Groups['value'].Value
          })
        }
      }
      if ($fieldCandidates.Count -gt 0) {
        $fieldIndent = ($fieldCandidates | Measure-Object -Property Indent -Minimum).Minimum
        foreach ($field in @($fieldCandidates | Where-Object { $_.Indent -eq $fieldIndent -and $_.Key -eq 'observation' })) {
          $observationScalar = Get-YamlScalarResult -RawValue $field.Value -Lines $Section.Lines -ValueLineIndex $field.Index -ParentIndent $field.Indent
          if ($observationScalar.IsNonEmpty) { return $true }
        }
      }
      continue
    }
    if ($item.Value -notmatch '^[A-Za-z_][A-Za-z0-9_]*:') {
      $observationScalar = Get-YamlScalarResult -RawValue $item.Value -Lines $Section.Lines -ValueLineIndex $item.Index -ParentIndent $itemIndent
      if ($observationScalar.IsNonEmpty) { return $true }
    }
  }
  return $false
}

function Get-RuleExampleParse {
  param([Parameter(Mandatory = $true)]$RuleRecord)

  $examples = [System.Collections.Generic.List[object]]::new()
  $parseErrors = [System.Collections.Generic.List[string]]::new()
  if (-not $RuleRecord.Fields.ContainsKey('examples')) {
    return [pscustomobject]@{ Examples = @(); Errors = @() }
  }

  $exampleField = $RuleRecord.Fields['examples']
  $exampleLines = [System.Collections.Generic.List[string]]::new()
  for ($lineIndex = $exampleField.Index + 1; $lineIndex -lt $RuleRecord.Lines.Count; $lineIndex++) {
    $line = $RuleRecord.Lines[$lineIndex]
    if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
    $indent = ([regex]::Match($line, '^ *')).Value.Length
    if ($indent -le $exampleField.Indent) { break }
    $exampleLines.Add($line)
  }
  if ($exampleLines.Count -eq 0) {
    return [pscustomobject]@{ Examples = @(); Errors = @() }
  }

  $items = [System.Collections.Generic.List[object]]::new()
  for ($index = 0; $index -lt $exampleLines.Count; $index++) {
    $match = [regex]::Match($exampleLines[$index], '^(?<indent> *)-\s*(?<value>.*)$')
    if ($match.Success) {
      $items.Add([pscustomobject]@{
        Index  = $index
        Indent = $match.Groups['indent'].Value.Length
        Value  = $match.Groups['value'].Value.Trim()
      })
    }
  }
  if ($items.Count -eq 0) {
    $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
    return [pscustomobject]@{ Examples = @(); Errors = $parseErrors.ToArray() }
  }

  $itemIndent = ($items | Measure-Object -Property Indent -Minimum).Minimum
  $topItems = @($items | Where-Object { $_.Indent -eq $itemIndent })
  $topItemIndexes = @{}
  foreach ($topItem in $topItems) { $topItemIndexes[$topItem.Index] = $true }
  for ($lineIndex = 0; $lineIndex -lt $exampleLines.Count; $lineIndex++) {
    $lineIndent = ([regex]::Match($exampleLines[$lineIndex], '^ *')).Value.Length
    if (($lineIndex -lt $topItems[0].Index) -or ($lineIndent -le $itemIndent -and -not $topItemIndexes.ContainsKey($lineIndex))) {
      $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
      break
    }
  }
  for ($itemNumber = 0; $itemNumber -lt $topItems.Count; $itemNumber++) {
    $item = $topItems[$itemNumber]
    $end = if ($itemNumber + 1 -lt $topItems.Count) { $topItems[$itemNumber + 1].Index } else { $exampleLines.Count }
    $rawFields = @{}

    $inline = Get-YamlInlineMapResult -RawValue $item.Value
    if ($inline.IsMap) {
      if (-not $inline.IsValid) {
        $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
        continue
      }
      if ($end -gt ($item.Index + 1)) {
        $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
        continue
      }
      foreach ($key in $inline.Fields.Keys) { $rawFields[$key] = $inline.Fields[$key] }
    } elseif ($item.Value -match '^source_id:[ \t]*(?<value>.*)$') {
      $rawFields['source_id'] = $Matches['value'].Trim()
      $blockFieldCandidates = [System.Collections.Generic.List[object]]::new()
      for ($cursor = $item.Index + 1; $cursor -lt $end; $cursor++) {
        $fieldMatch = [regex]::Match($exampleLines[$cursor], '^ +(?<key>[A-Za-z_][A-Za-z0-9_]*):[ \t]*(?<value>.*)$')
        if ($fieldMatch.Success) {
          $blockFieldCandidates.Add([pscustomobject]@{
            Indent = ([regex]::Match($exampleLines[$cursor], '^ *')).Value.Length
            Key    = $fieldMatch.Groups['key'].Value
            Value  = $fieldMatch.Groups['value'].Value.Trim()
          })
        } else {
          $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
        }
      }
      if ($blockFieldCandidates.Count -gt 0) {
        $blockFieldIndent = ($blockFieldCandidates | Measure-Object -Property Indent -Minimum).Minimum
        foreach ($field in @($blockFieldCandidates | Where-Object { $_.Indent -eq $blockFieldIndent })) {
          $rawFields[$field.Key] = $field.Value
        }
      }
    } else {
      $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
      continue
    }

    $complete = $true
    $scalarFields = @{}
    foreach ($key in @('source_id', 'timestamp', 'excerpt')) {
      if (-not $rawFields.ContainsKey($key)) {
        $complete = $false
        continue
      }
      $scalar = Get-YamlScalarResult -RawValue $rawFields[$key]
      if (-not $scalar.IsNonEmpty) { $complete = $false; continue }
      $scalarFields[$key] = $scalar.Value
    }
    if (-not $complete) {
      $parseErrors.Add("voice rule $($RuleRecord.Id) contains incomplete example item")
      continue
    }

    $sourceId = $scalarFields['source_id']
    $timestamp = $scalarFields['timestamp']
    $excerpt = $scalarFields['excerpt']
    if (-not (Test-VoiceTimestamp $timestamp)) {
      $parseErrors.Add("voice rule $($RuleRecord.Id) example has invalid timestamp: $timestamp")
      continue
    }
    $examples.Add([pscustomobject]@{ SourceId = $sourceId; Timestamp = $timestamp; Excerpt = $excerpt })
  }

  return [pscustomobject]@{ Examples = $examples.ToArray(); Errors = $parseErrors.ToArray() }
}

function Get-VoiceSchemaErrors {
  param(
    [Parameter(Mandatory = $true)][string]$ProfileContent,
    [Parameter(Mandatory = $true)][string]$SourcesContent
  )

  $errors = [System.Collections.Generic.List[string]]::new()
  $profileLines = @((Get-YamlPayload $ProfileContent) -split '\r?\n')
  $sourceLines = @((Get-YamlPayload $SourcesContent) -split '\r?\n')
  $rulesSection = Get-YamlSection -Lines $profileLines -Key 'voice_rules'
  $sourceSection = Get-YamlSection -Lines $sourceLines -Key 'sources'
  $sourceById = @{}

  if (-not $sourceSection.Found) {
    $errors.Add('voice source ledger must contain sources')
  } else {
    $sourceParse = Get-YamlListRecords -Section $sourceSection -IdKey 'source_id'
    if ($sourceParse.UnparsedCount -gt 0) {
      $errors.Add('voice source ledger contains unparsed records or records without source_id')
    }

    $hasHoldout = $false
    $seenSourceIds = @{}
    foreach ($sourceRecord in $sourceParse.Records) {
      $sourceId = $sourceRecord.Id
      $sourceIdIsValid = $sourceRecord.IdScalar.IsNonEmpty
      $sourceIdIsUnique = $false
      if (-not $sourceIdIsValid) {
        $errors.Add('voice source record has empty or null source_id')
      } elseif ($seenSourceIds.ContainsKey($sourceId)) {
        $errors.Add("duplicate voice source_id: $sourceId")
      } else {
        $sourceIdIsUnique = $true
        $seenSourceIds[$sourceId] = $true
        $sourceById[$sourceId] = $sourceRecord
      }
      $fieldScalars = @{}
      foreach ($field in @('source', 'transcript_type', 'speaker_exclusions', 'word_count', 'split', 'holdout')) {
        $fieldScalar = Get-YamlRecordFieldScalarResult -Record $sourceRecord -FieldName $field
        $fieldScalars[$field] = $fieldScalar
        if (-not $fieldScalar.IsNonEmpty) {
          $errors.Add("voice source $sourceId missing required field: $field")
        }
      }

      $split = if ($fieldScalars['split'].IsNonEmpty) { $fieldScalars['split'].Value } else { '' }
      $holdout = if ($fieldScalars['holdout'].IsNonEmpty) { $fieldScalars['holdout'].Value.ToLowerInvariant() } else { '' }
      if ($split -and $split -notin @('training', 'holdout')) {
        $errors.Add("voice source $sourceId split must be training or holdout")
      }
      if ($holdout -and $holdout -notin @('true', 'false')) {
        $errors.Add("voice source $sourceId holdout must be true or false")
      }
      if (($split -eq 'training' -and $holdout -ne 'false') -or ($split -eq 'holdout' -and $holdout -ne 'true')) {
        $errors.Add("voice source $sourceId split and holdout must agree")
      }
      if ($sourceIdIsValid -and $sourceIdIsUnique -and $split -eq 'holdout' -and $holdout -eq 'true') { $hasHoldout = $true }
    }

    if (-not $hasHoldout) {
      $errors.Add('voice source ledger must contain at least one separate split: holdout, holdout: true source')
    }
  }

  if (-not $rulesSection.Found) {
    $errors.Add('voice profile must contain voice_rules')
    return $errors.ToArray()
  }

  $rulesParse = Get-YamlListRecords -Section $rulesSection -IdKey 'rule_id'
  if ($rulesParse.UnparsedCount -gt 0) {
    $errors.Add('voice_rules contains non-empty unparsed records')
  }

  $rulesAreExplicitlyEmpty = $rulesParse.Records.Count -eq 0 -and -not $rulesParse.BodyHasContent -and $rulesSection.InlineValue -in @('', '[]')
  if ($rulesAreExplicitlyEmpty) {
    $statusSection = Get-YamlSection -Lines $profileLines -Key 'profile_status'
    $observationsSection = Get-YamlSection -Lines $profileLines -Key 'provisional_observations'
    $statusScalar = Get-YamlScalarResult -RawValue $statusSection.InlineValue
    $isProvisional = $statusSection.Found -and $statusScalar.IsNonEmpty -and $statusScalar.Value -eq 'provisional'
    $hasObservations = Test-ProvisionalObservationSection $observationsSection
    if (-not $isProvisional -or -not $hasObservations) {
      $errors.Add('empty voice_rules require profile_status: provisional and non-empty provisional_observations')
    }
  }

  foreach ($ruleRecord in $rulesParse.Records) {
    $ruleId = $ruleRecord.Id
    foreach ($field in @('rule', 'scope', 'examples', 'counter_evidence', 'confidence', 'do_not_imitate')) {
      $fieldExists = $ruleRecord.Fields.ContainsKey($field)
      $fieldHasValue = $fieldExists -and ($field -eq 'examples' -or [bool](Get-UnquotedValue $ruleRecord.Fields[$field].Value))
      if (-not $fieldHasValue) {
        $errors.Add("voice rule $ruleId missing required field: $field")
      }
    }

    $exampleParse = Get-RuleExampleParse $ruleRecord
    foreach ($parseError in $exampleParse.Errors) { $errors.Add($parseError) }
    $examples = @($exampleParse.Examples)

    if ($examples.Count -lt 2) {
      $errors.Add("voice rule $ruleId must have at least two timestamped examples")
    } else {
      $sourceIds = @($examples | ForEach-Object { $_.SourceId } | Select-Object -Unique)
      if ($sourceIds.Count -lt 2) {
        $errors.Add("voice rule $ruleId examples must use different source IDs")
      }
      foreach ($sourceId in $sourceIds) {
        if (-not $sourceById.ContainsKey($sourceId)) {
          $errors.Add("voice rule $ruleId example source is unknown: $sourceId")
          continue
        }
        $sourceRecord = $sourceById[$sourceId]
        $splitScalar = Get-YamlRecordFieldScalarResult -Record $sourceRecord -FieldName 'split'
        $holdoutScalar = Get-YamlRecordFieldScalarResult -Record $sourceRecord -FieldName 'holdout'
        $split = if ($splitScalar.IsNonEmpty) { $splitScalar.Value } else { '' }
        $holdout = if ($holdoutScalar.IsNonEmpty) { $holdoutScalar.Value.ToLowerInvariant() } else { '' }
        if ($split -ne 'training' -or $holdout -ne 'false') {
          $errors.Add("voice rule $ruleId example source must be training and holdout false: $sourceId")
        }
      }
    }
  }

  return $errors.ToArray()
}

if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) {
  throw 'SKILL.md is missing'
}

$content = Get-Content -Raw -Encoding UTF8 $skillPath
$intakeContent = Get-Content -Raw -Encoding UTF8 $intakePath
$evidenceContent = Get-Content -Raw -Encoding UTF8 $evidencePath
$routes = [ordered]@{
  intake             = 'references/01-intake.md'
  structure          = 'references/02-structure.md'
  evidence_pack      = 'references/03-evidence-pack.md'
  draft              = 'references/04-draft.md'
  voice              = 'references/05-artur-voice.md'
  spoken_audit       = 'references/06-spoken-audit.md'
  russian_edit       = 'references/07-russian-edit.md'
  retention_evidence = 'references/08-retention-evidence.md'
  human_approval     = 'references/09-human-approval.md'
  production_handoff = 'references/10-production-handoff.md'
}

foreach ($entry in $routes.GetEnumerator()) {
  if ($content -notmatch "(?m)^\s*\|?\s*$([regex]::Escape($entry.Key))\s*\|") {
    throw "Missing exact stage ID: $($entry.Key)"
  }
  if (-not $content.Contains($entry.Value)) {
    throw "Missing exact module path: $($entry.Value)"
  }
}

foreach ($required in @('Canvas is optional', 'approved_by_artur')) {
  if (-not $content.Contains($required)) {
    throw "Missing router contract: $required"
  }
}

$unconditionalLoadPatterns = @(
  '(?im)\b(?:load|read)\s+all\s+(?:ten\s+)?(?:reference files|references|modules)\b',
  '(?im)\b(?:always|unconditionally)\s+(?:load|read)\s+(?:every|all)\s+(?:reference files|references|modules)\b',
  '(?im)\b(?:load|read)\s+references/\*'
)

foreach ($pattern in $unconditionalLoadPatterns) {
  if ($content -match $pattern) {
    throw "Router must not load all reference files unconditionally: $($Matches[0])"
  }
}

$contractErrors = [System.Collections.Generic.List[string]]::new()
$canonicalDiscoveryOrder = 'Canonical discovery order: current_request > project_identity > canvas > approved_state > existing_script > sources'
if (-not $content.Contains($canonicalDiscoveryOrder)) {
  $contractErrors.Add('SKILL.md must use the canonical six-step discovery order')
}
if (-not $intakeContent.Contains($canonicalDiscoveryOrder)) {
  $contractErrors.Add('01-intake.md must define the canonical six-step discovery order')
}

$noSourceRule = 'No-source rule: `source: null` is allowed only with `source_type: unverified` and `verification_state: unverified`.'
if (-not $evidenceContent.Contains($noSourceRule)) {
  $contractErrors.Add('03-evidence-pack.md must define the valid no-source representation')
}

if ($contractErrors.Count -gt 0) {
  throw ($contractErrors -join [Environment]::NewLine)
}

foreach ($requiredPath in @($voiceModulePath, $voiceProfilePath, $voiceSourcesPath, $validVoiceFixturePath, $invalidVoiceFixturePath)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    throw "Voice schema file is missing: $requiredPath"
  }
}

$voiceProfileContent = Get-Content -Raw -Encoding UTF8 $voiceProfilePath
$voiceSourcesContent = Get-Content -Raw -Encoding UTF8 $voiceSourcesPath
$liveVoiceErrors = @(Get-VoiceSchemaErrors -ProfileContent $voiceProfileContent -SourcesContent $voiceSourcesContent)
if ($liveVoiceErrors.Count -gt 0) {
  throw ($liveVoiceErrors -join [Environment]::NewLine)
}

$validVoiceFixtureContent = Get-Content -Raw -Encoding UTF8 $validVoiceFixturePath
$validVoiceErrors = @(Get-VoiceSchemaErrors -ProfileContent $validVoiceFixtureContent -SourcesContent $validVoiceFixtureContent)
if ($validVoiceErrors.Count -gt 0) {
  throw "Valid voice fixture was rejected: $($validVoiceErrors -join '; ')"
}

$invalidVoiceFixtureContent = Get-Content -Raw -Encoding UTF8 $invalidVoiceFixturePath
$invalidVoiceErrors = @(Get-VoiceSchemaErrors -ProfileContent $invalidVoiceFixtureContent -SourcesContent $invalidVoiceFixtureContent)
$expectedInvalidReason = 'voice rule V99 missing required field: counter_evidence'
if ($invalidVoiceErrors.Count -ne 1 -or $invalidVoiceErrors[0] -ne $expectedInvalidReason) {
  throw "Invalid voice fixture must fail only for '$expectedInvalidReason'; actual: $($invalidVoiceErrors -join '; ')"
}

$probeFailures = [System.Collections.Generic.List[string]]::new()

$fourSpaceRuleProbe = @'
profile_status: active
voice_rules:
    - rule_id: V04
      rule: "Four-space YAML record"
      scope: [explanation]
      examples:
        - {source_id: F01, timestamp: "00:42", excerpt: "first fixture excerpt"}
        - {source_id: F02, timestamp: "03:11", excerpt: "second fixture excerpt"}
      confidence: medium
      do_not_imitate: "Synthetic caption noise."
sources:
  - source_id: F01
    source: "C:\\fixtures\\F01.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: training
    holdout: false
  - source_id: F02
    source: "C:\\fixtures\\F02.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: training
    holdout: false
  - source_id: F03
    source: "C:\\fixtures\\F03.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: holdout
    holdout: true
'@
$fourSpaceErrors = @(Get-VoiceSchemaErrors -ProfileContent $fourSpaceRuleProbe -SourcesContent $fourSpaceRuleProbe)
if ($fourSpaceErrors -notcontains 'voice rule V04 missing required field: counter_evidence') {
  $probeFailures.Add("four-space YAML rule was not validated: $($fourSpaceErrors -join '; ')")
}
$fourSpaceValidProbe = $fourSpaceRuleProbe -replace '(?m)^      confidence:', "      counter_evidence: `"none`"`r`n      confidence:"
$fourSpaceValidErrors = @(Get-VoiceSchemaErrors -ProfileContent $fourSpaceValidProbe -SourcesContent $fourSpaceValidProbe)
if ($fourSpaceValidErrors.Count -gt 0) {
  $probeFailures.Add("valid four-space YAML rule was rejected: $($fourSpaceValidErrors -join '; ')")
}

$emptyNonProvisionalProbe = @'
voice_rules: []
sources:
  - source_id: F03
    source: "C:\\fixtures\\F03.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: holdout
    holdout: true
'@
$emptyNonProvisionalErrors = @(Get-VoiceSchemaErrors -ProfileContent $emptyNonProvisionalProbe -SourcesContent $emptyNonProvisionalProbe)
$expectedProvisionalReason = 'empty voice_rules require profile_status: provisional and non-empty provisional_observations'
if ($emptyNonProvisionalErrors -notcontains $expectedProvisionalReason) {
  $probeFailures.Add("empty non-provisional profile was accepted: $($emptyNonProvisionalErrors -join '; ')")
}

$unknownSourceProbe = $validVoiceFixtureContent -replace 'source_id: F02, timestamp:', 'source_id: F99, timestamp:'
$unknownSourceErrors = @(Get-VoiceSchemaErrors -ProfileContent $unknownSourceProbe -SourcesContent $unknownSourceProbe)
if ($unknownSourceErrors -notcontains 'voice rule V01 example source is unknown: F99') {
  $probeFailures.Add("unknown example source was accepted: $($unknownSourceErrors -join '; ')")
}

$holdoutSourceProbe = $validVoiceFixtureContent -replace 'source_id: F02, timestamp:', 'source_id: F03, timestamp:'
$holdoutSourceErrors = @(Get-VoiceSchemaErrors -ProfileContent $holdoutSourceProbe -SourcesContent $holdoutSourceProbe)
if ($holdoutSourceErrors -notcontains 'voice rule V01 example source must be training and holdout false: F03') {
  $probeFailures.Add("holdout example source was accepted: $($holdoutSourceErrors -join '; ')")
}

$missingLedgerFieldProbe = @'
profile_status: provisional
voice_rules: []
provisional_observations:
  - observation_id: P01
    status: corpus_insufficient
sources:
  - source_id: F01
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: training
    holdout: false
  - source_id: F03
    source: "C:\\fixtures\\F03.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: holdout
    holdout: true
'@
$missingLedgerFieldErrors = @(Get-VoiceSchemaErrors -ProfileContent $missingLedgerFieldProbe -SourcesContent $missingLedgerFieldProbe)
if ($missingLedgerFieldErrors -notcontains 'voice source F01 missing required field: source') {
  $probeFailures.Add("missing ledger source field was accepted: $($missingLedgerFieldErrors -join '; ')")
}

$unparsedRuleProbe = $fourSpaceRuleProbe -replace '- rule_id: V04', '- unexpected_key: V04'
$unparsedRuleErrors = @(Get-VoiceSchemaErrors -ProfileContent $unparsedRuleProbe -SourcesContent $unparsedRuleProbe)
if ($unparsedRuleErrors -notcontains 'voice_rules contains non-empty unparsed records') {
  $probeFailures.Add("non-empty unparsed rule record was accepted: $($unparsedRuleErrors -join '; ')")
}

$fixtureSourceSection = [regex]::Match($validVoiceFixtureContent, '(?ms)^sources:.*?(?=^```[ \t]*$)').Value

$nestedStatusProfile = @'
voice_rules: []
metadata:
  profile_status: provisional
provisional_observations:
  - observation_id: P01
    observation: "semantic observation"
'@
$nestedStatusProbe = "$nestedStatusProfile`r`n$fixtureSourceSection"
$nestedStatusErrors = @(Get-VoiceSchemaErrors -ProfileContent $nestedStatusProbe -SourcesContent $nestedStatusProbe)
if ($nestedStatusErrors -notcontains $expectedProvisionalReason) {
  $probeFailures.Add("nested profile_status satisfied the top-level contract: $($nestedStatusErrors -join '; ')")
}

$nestedObservationsProfile = @'
profile_status: provisional
voice_rules: []
metadata:
  provisional_observations:
    - observation_id: P01
      observation: "semantic observation"
'@
$nestedObservationsProbe = "$nestedObservationsProfile`r`n$fixtureSourceSection"
$nestedObservationsErrors = @(Get-VoiceSchemaErrors -ProfileContent $nestedObservationsProbe -SourcesContent $nestedObservationsProbe)
if ($nestedObservationsErrors -notcontains $expectedProvisionalReason) {
  $probeFailures.Add("nested provisional_observations satisfied the top-level contract: $($nestedObservationsErrors -join '; ')")
}

$semanticObservationCases = [ordered]@{
  null_item = '  - null'
  empty_map = '  - {}'
  empty_string = '  - ""'
  comments_only = '  # no observation'
  empty = ''
  nested_substitute = "  metadata:`r`n    observation: `"nested substitute`""
  nested_under_record = "  - observation_id: P01`r`n    metadata:`r`n      observation: `"nested substitute`""
}
foreach ($case in $semanticObservationCases.GetEnumerator()) {
  $profile = "profile_status: provisional`r`nvoice_rules: []`r`nprovisional_observations:`r`n$($case.Value)"
  $probe = "$profile`r`n$fixtureSourceSection"
  $caseErrors = @(Get-VoiceSchemaErrors -ProfileContent $probe -SourcesContent $probe)
  if ($caseErrors -notcontains $expectedProvisionalReason) {
    $probeFailures.Add("semantic-empty provisional observation '$($case.Key)' was accepted: $($caseErrors -join '; ')")
  }
}

foreach ($inlineValue in @('[null]', '[{}]', '[""]')) {
  $profile = "profile_status: provisional`r`nvoice_rules: []`r`nprovisional_observations: $inlineValue"
  $probe = "$profile`r`n$fixtureSourceSection"
  $inlineObservationErrors = @(Get-VoiceSchemaErrors -ProfileContent $probe -SourcesContent $probe)
  if ($inlineObservationErrors -notcontains $expectedProvisionalReason) {
    $probeFailures.Add("semantic-empty inline provisional observations '$inlineValue' were accepted: $($inlineObservationErrors -join '; ')")
  }
}

$secondInlineExample = '      - {source_id: F02, timestamp: "03:11", excerpt: "second fixture excerpt"}'
$validBlockExample = @'
      - source_id: F02
        timestamp: "03:11"
        excerpt: "second fixture excerpt"
'@
$validBlockProbe = $validVoiceFixtureContent.Replace($secondInlineExample, $validBlockExample)
$validBlockErrors = @(Get-VoiceSchemaErrors -ProfileContent $validBlockProbe -SourcesContent $validBlockProbe)
if ($validBlockErrors.Count -ne 0) {
  $probeFailures.Add("complete block-style example was rejected: $($validBlockErrors -join '; ')")
}

$blockHoldoutExample = @'
      - source_id: F03
        timestamp: "04:22"
        excerpt: "holdout block example"
'@
$blockHoldoutProbe = $validVoiceFixtureContent.Replace($secondInlineExample, "$secondInlineExample`r`n$blockHoldoutExample")
$blockHoldoutErrors = @(Get-VoiceSchemaErrors -ProfileContent $blockHoldoutProbe -SourcesContent $blockHoldoutProbe)
if ($blockHoldoutErrors -notcontains 'voice rule V01 example source must be training and holdout false: F03') {
  $probeFailures.Add("block-style holdout example was ignored: $($blockHoldoutErrors -join '; ')")
}

$blockUnknownExample = @'
      - source_id: F99
        timestamp: "04:22"
        excerpt: "unknown block example"
'@
$blockUnknownProbe = $validVoiceFixtureContent.Replace($secondInlineExample, "$secondInlineExample`r`n$blockUnknownExample")
$blockUnknownErrors = @(Get-VoiceSchemaErrors -ProfileContent $blockUnknownProbe -SourcesContent $blockUnknownProbe)
if ($blockUnknownErrors -notcontains 'voice rule V01 example source is unknown: F99') {
  $probeFailures.Add("block-style unknown example was ignored: $($blockUnknownErrors -join '; ')")
}

$incompleteInlineExample = '      - {source_id: F01, timestamp: "05:00"}'
$incompleteInlineProbe = $validVoiceFixtureContent.Replace($secondInlineExample, "$secondInlineExample`r`n$incompleteInlineExample")
$incompleteInlineErrors = @(Get-VoiceSchemaErrors -ProfileContent $incompleteInlineProbe -SourcesContent $incompleteInlineProbe)
if ($incompleteInlineErrors -notcontains 'voice rule V01 contains incomplete example item') {
  $probeFailures.Add("incomplete inline example was ignored: $($incompleteInlineErrors -join '; ')")
}

$nestedBlockExample = @'
      - source_id: F01
        metadata:
          timestamp: "05:00"
          excerpt: "nested fields are not example fields"
'@
$nestedBlockProbe = $validVoiceFixtureContent.Replace($secondInlineExample, "$secondInlineExample`r`n$nestedBlockExample")
$nestedBlockErrors = @(Get-VoiceSchemaErrors -ProfileContent $nestedBlockProbe -SourcesContent $nestedBlockProbe)
if ($nestedBlockErrors -notcontains 'voice rule V01 contains incomplete example item') {
  $probeFailures.Add("nested block example fields were accepted as direct fields: $($nestedBlockErrors -join '; ')")
}

$firstInlineExample = '      - {source_id: F01, timestamp: "00:42", excerpt: "first fixture excerpt"}'
$strayExampleProbe = $validVoiceFixtureContent.Replace($firstInlineExample, "      stray: true`r`n$firstInlineExample")
$strayExampleErrors = @(Get-VoiceSchemaErrors -ProfileContent $strayExampleProbe -SourcesContent $strayExampleProbe)
if ($strayExampleErrors -notcontains 'voice rule V01 contains incomplete example item') {
  $probeFailures.Add("non-list examples content was ignored: $($strayExampleErrors -join '; ')")
}

$invalidTimestampExample = '      - {source_id: F01, timestamp: "not-a-time", excerpt: "invalid timestamp"}'
$invalidTimestampProbe = $validVoiceFixtureContent.Replace($secondInlineExample, "$secondInlineExample`r`n$invalidTimestampExample")
$invalidTimestampErrors = @(Get-VoiceSchemaErrors -ProfileContent $invalidTimestampProbe -SourcesContent $invalidTimestampProbe)
if ($invalidTimestampErrors -notcontains 'voice rule V01 example has invalid timestamp: not-a-time') {
  $probeFailures.Add("invalid-timestamp example was ignored: $($invalidTimestampErrors -join '; ')")
}

$emptySourceIdProbe = $validVoiceFixtureContent -replace '(?m)^  - source_id: F01$', '  - source_id: ""'
$emptySourceIdErrors = @(Get-VoiceSchemaErrors -ProfileContent $emptySourceIdProbe -SourcesContent $emptySourceIdProbe)
if ($emptySourceIdErrors -notcontains 'voice source record has empty or null source_id') {
  $probeFailures.Add("empty source_id was accepted: $($emptySourceIdErrors -join '; ')")
}

$nullSourceIdProbe = $validVoiceFixtureContent -replace '(?m)^  - source_id: F01$', '  - source_id: null'
$nullSourceIdErrors = @(Get-VoiceSchemaErrors -ProfileContent $nullSourceIdProbe -SourcesContent $nullSourceIdProbe)
if ($nullSourceIdErrors -notcontains 'voice source record has empty or null source_id') {
  $probeFailures.Add("null source_id was accepted: $($nullSourceIdErrors -join '; ')")
}

$holdoutAliasBlock = @'
  - source_id: F01
    source: "C:\\fixtures\\F01-holdout.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: holdout
    holdout: true
'@
$duplicateSourceProbe = $validVoiceFixtureContent.Replace('sources:', "sources:`r`n$holdoutAliasBlock")
$duplicateSourceErrors = @(Get-VoiceSchemaErrors -ProfileContent $duplicateSourceProbe -SourcesContent $duplicateSourceProbe)
if ($duplicateSourceErrors -notcontains 'duplicate voice source_id: F01') {
  $probeFailures.Add("duplicate training/holdout source_id was accepted: $($duplicateSourceErrors -join '; ')")
}

foreach ($field in @('source', 'transcript_type', 'speaker_exclusions', 'word_count', 'split', 'holdout')) {
  $fieldRegex = [regex]::new('(?m)^    ' + [regex]::Escape($field) + ':.*$')
  $nullFieldProbe = $fieldRegex.Replace($validVoiceFixtureContent, "    ${field}: null", 1)
  $nullFieldErrors = @(Get-VoiceSchemaErrors -ProfileContent $nullFieldProbe -SourcesContent $nullFieldProbe)
  $expectedNullFieldReason = "voice source F01 missing required field: $field"
  if ($nullFieldErrors -notcontains $expectedNullFieldReason) {
    $probeFailures.Add("null ledger field '$field' was accepted: $($nullFieldErrors -join '; ')")
  }

  $emptyFieldProbe = $fieldRegex.Replace($validVoiceFixtureContent, "    ${field}: `"`"", 1)
  $emptyFieldErrors = @(Get-VoiceSchemaErrors -ProfileContent $emptyFieldProbe -SourcesContent $emptyFieldProbe)
  if ($emptyFieldErrors -notcontains $expectedNullFieldReason) {
    $probeFailures.Add("empty ledger field '$field' was accepted: $($emptyFieldErrors -join '; ')")
  }
}

$commentOnlySourceRegex = [regex]::new('(?m)^    source:.*$')
$commentOnlySourceProbe = $commentOnlySourceRegex.Replace($validVoiceFixtureContent, '    source: # no scalar value', 1)
$commentOnlySourceErrors = @(Get-VoiceSchemaErrors -ProfileContent $commentOnlySourceProbe -SourcesContent $commentOnlySourceProbe)
if ($commentOnlySourceErrors -notcontains 'voice source F01 missing required field: source') {
  $probeFailures.Add("comment-only ledger source was accepted: $($commentOnlySourceErrors -join '; ')")
}

foreach ($indicator in @('|', '>')) {
  $profile = @"
profile_status: provisional
voice_rules: []
provisional_observations:
  - observation_id: P01
    observation: $indicator
"@
  $probe = "$profile`r`n$fixtureSourceSection"
  $observationBlockErrors = @(Get-VoiceSchemaErrors -ProfileContent $probe -SourcesContent $probe)
  if ($observationBlockErrors -notcontains $expectedProvisionalReason) {
    $label = if ($indicator -eq '|') { 'OBS_EMPTY_LITERAL' } else { 'OBS_EMPTY_FOLDED' }
    $probeFailures.Add("${label}=empty block scalar observation was accepted")
  }
}

$nestedInlineExample = '      - {metadata: {dummy: true, source_id: F02, timestamp: "03:11", excerpt: "nested only"}}'
$nestedInlineProbe = $validVoiceFixtureContent.Replace($secondInlineExample, $nestedInlineExample)
$nestedInlineErrors = @(Get-VoiceSchemaErrors -ProfileContent $nestedInlineProbe -SourcesContent $nestedInlineProbe)
if ($nestedInlineErrors -notcontains 'voice rule V01 contains incomplete example item') {
  $probeFailures.Add("INLINE_NESTED_FIELDS=nested inline-map fields were accepted: $($nestedInlineErrors -join '; ')")
}

$badSecondsExample = '      - {source_id: F02, timestamp: "03:99", excerpt: "invalid seconds"}'
$badSecondsProbe = $validVoiceFixtureContent.Replace($secondInlineExample, $badSecondsExample)
$badSecondsErrors = @(Get-VoiceSchemaErrors -ProfileContent $badSecondsProbe -SourcesContent $badSecondsProbe)
if ($badSecondsErrors -notcontains 'voice rule V01 example has invalid timestamp: 03:99') {
  $probeFailures.Add("TIMESTAMP_BAD_SECONDS=03:99 was accepted: $($badSecondsErrors -join '; ')")
}

foreach ($field in @('source', 'transcript_type', 'speaker_exclusions', 'word_count')) {
  $semanticFieldRegex = [regex]::new('(?m)^    ' + [regex]::Escape($field) + ':.*$')
  $semanticCases = [ordered]@{
    NULL_COMMENT  = "    ${field}: null # no value"
    EMPTY_COMMENT = "    ${field}: `"`" # no value"
    EMPTY_BLOCK   = "    ${field}: |"
  }
  foreach ($case in $semanticCases.GetEnumerator()) {
    $semanticFieldProbe = $semanticFieldRegex.Replace($validVoiceFixtureContent, $case.Value, 1)
    $semanticFieldErrors = @(Get-VoiceSchemaErrors -ProfileContent $semanticFieldProbe -SourcesContent $semanticFieldProbe)
    $expectedSemanticFieldReason = "voice source F01 missing required field: $field"
    if ($semanticFieldErrors -notcontains $expectedSemanticFieldReason) {
      $probeFailures.Add("${field}_$($case.Key)=semantic-empty ledger value was accepted: $($semanticFieldErrors -join '; ')")
    }
  }
}

$holdoutIdRegex = [regex]::new('(?m)^  - source_id: F03$')
$semanticIdCases = [ordered]@{
  '|'                         = @{ Value = '|'; Expected = 'voice source record has empty or null source_id' }
  '>'                         = @{ Value = '>'; Expected = 'voice source record has empty or null source_id' }
  'null # semantic-null'      = @{ Value = 'null # semantic-null'; Expected = 'voice source record has empty or null source_id' }
  'F01 # semantic-duplicate'  = @{ Value = 'F01 # semantic-duplicate'; Expected = 'duplicate voice source_id: F01' }
}
foreach ($case in $semanticIdCases.GetEnumerator()) {
  $semanticIdProbe = $holdoutIdRegex.Replace($validVoiceFixtureContent, "  - source_id: $($case.Value.Value)", 1)
  $semanticIdErrors = @(Get-VoiceSchemaErrors -ProfileContent $semanticIdProbe -SourcesContent $semanticIdProbe)
  if ($semanticIdErrors -notcontains $case.Value.Expected) {
    $probeFailures.Add("ID[$($case.Key)]=semantic source ID was accepted: $($semanticIdErrors -join '; ')")
  }
}

if ($probeFailures.Count -gt 0) {
  throw ("Voice schema regression probes failed:" + [Environment]::NewLine + ($probeFailures -join [Environment]::NewLine))
}

Write-Output 'PASS router and voice schema contract'
