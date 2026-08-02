# Test log

## Task 2 — package validator

### RED

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
```

Exit code: `1`

Output: `CommandNotFoundException` for the intentionally absent `scripts\validate-package.ps1`.

### GREEN

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
```

Exit code: `0`

Output:

```text
PASS package validator
```

### Additional skill-authoring validation

Command required by `skill-creator`:

```powershell
python C:\Users\magme\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Projects\Video\.agents\skills\youtube-editorial\tests\fixtures\package-valid
```

Exit code: `0`

Output:

```text
Skill is valid!
```

## Task 3 — editorial router and early-stage modules

### RED

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-router.ps1
```

Exit code: `1`

Output:

```text
SKILL.md is missing
```

The failure was expected: `test-router.ps1` existed while `SKILL.md` and the routed modules did not.

### GREEN

Commands and results:

```text
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-router.ps1
PASS router contract
Exit code: 0

powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
PASS package validator
Exit code: 0
```

### Router quality checks

```text
SKILL.md words: 340
Description characters: 201
Description starts with "Use when ": True
```

## Task 3 — fix round 1

### RED

Commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-router.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
```

Both exited `1`.

```text
SKILL.md must use the canonical six-step discovery order
01-intake.md must define the canonical six-step discovery order
03-evidence-pack.md must define the valid no-source representation

Es wurde kein Parameter gefunden, der dem Parameternamen "AllowPlannedMissingModules" entspricht.
Expected staged live-package validation to succeed
Expected staged validation to report the unexpected missing reference
```

### GREEN

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-router.ps1
PASS router contract
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
PASS package validator
Exit code: 0
```

Direct validation modes:

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot C:\Projects\Video\.agents\skills\youtube-editorial -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot C:\Projects\Video\.agents\skills\youtube-editorial
ERROR referenced file is missing: references/05-artur-voice.md
ERROR referenced file is missing: references/06-spoken-audit.md
ERROR referenced file is missing: references/07-russian-edit.md
ERROR referenced file is missing: references/08-retention-evidence.md
ERROR referenced file is missing: references/09-human-approval.md
ERROR referenced file is missing: references/10-production-handoff.md
Exit code: 1

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot C:\Projects\Video\.agents\skills\youtube-editorial\tests\fixtures\package-invalid -AllowPlannedMissingModules
ERROR frontmatter must contain name youtube-editorial and a non-empty description
ERROR referenced file is missing: references/missing.md
Exit code: 1
```

## Task 3 — fix round 2

### RED

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
```

Exit code: `1`

```text
Resolve-Path : Der Pfad "C:\Projects\Video\.agents\skills\youtube-editorial\tests\fixtures\package-staged" kann nicht gefunden werden, da er nicht vorhanden ist.
Expected strict staged-fixture validation to report: references/05-artur-voice.md
```

### GREEN

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-router.ps1
PASS router contract
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\Video\.agents\skills\youtube-editorial\tests\test-package.ps1
PASS package validator
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot C:\Projects\Video\.agents\skills\youtube-editorial -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot tests\fixtures\package-staged
ERROR referenced file is missing: references/05-artur-voice.md
ERROR referenced file is missing: references/06-spoken-audit.md
ERROR referenced file is missing: references/07-russian-edit.md
ERROR referenced file is missing: references/08-retention-evidence.md
ERROR referenced file is missing: references/09-human-approval.md
ERROR referenced file is missing: references/10-production-handoff.md
Exit code: 1

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot tests\fixtures\package-staged -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial\tests\fixtures\package-staged
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot tests\fixtures\package-staged\unexpected -AllowPlannedMissingModules
ERROR referenced file is missing: references/missing.md
Exit code: 1

git diff --check
Exit code: 0
```

Point-in-time evidence on 2026-08-02: strict live-package validation exited `1` and reported the six absent planned modules. This result is not a permanent test assertion because Tasks 4–6 will add those files.

## Task 4 — Artur voice profile system

### RED

The voice-schema assertions were added to `tests/test-router.ps1` before any Task 4 profile or fixture file existed.

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
Voice schema file is missing: C:\Projects\Video\.agents\skills\youtube-editorial\profiles\artur-voice.md
EXIT_CODE=1
```

The failure was expected and was caused by the missing profile implementation.

### Corpus gate

Read-only local inventory excluded `C:\Projects\Video\2026-grill-me-top-5-skills` entirely. The two safe candidates were:

```text
A01 master_nomusic_transcript.json: 1593 full_text words, 185 timestamped automatic segments
A02 SCRIPT-8-10-MIN-RECORDING.md: 1958 file-level words, recording script with non-spoken directions
```

This is not 3-5 verified transcripts or 4,000-8,000 verified spoken words. The live profile therefore contains no approved voice rule and records only corpus insufficiency under `provisional_observations`.

### GREEN

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
PASS router and voice schema contract
EXIT_CODE=0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-package.ps1
PASS package validator
PACKAGE_TEST_EXIT=0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-package.ps1 -SkillRoot . -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial
STAGED_VALIDATOR_EXIT=0

> python C:\Users\magme\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
Skill is valid!
QUICK_VALIDATE_EXIT=0
```

The first implementation run exposed a test-regex defect: horizontal indentation after `voice_rules:` and `rule_id:` was consumed as cross-line whitespace, so the invalid fixture was not parsed. The parser was narrowed to horizontal whitespace, then the same test passed.

### Intended invalid-fixture reason

```text
PASS router and voice schema contract
INVALID_REJECTED voice rule V99 missing required field: counter_evidence
PASS invalid fixture intended reason only
Exit code: 0
```

Mutation checks also caught a missing `do_not_imitate`, duplicate example source IDs, and a missing holdout. `git diff --check` exited `0`.

Strict live-package validation still exits `1` only for the five planned Task 5-6 modules (`references/06-spoken-audit.md` through `references/10-production-handoff.md`).

## Task 4 — fix round 2

### RED

The round-2 regression probes were added before the validator changed. The aggregate run exited `1` and showed that nested provisional markers, semantic-empty observations, malformed or ignored examples, and invalid ledger identities/scalars were accepted:

```text
Voice schema regression probes failed:
nested profile_status satisfied the top-level contract:
nested provisional_observations satisfied the top-level contract:
semantic-empty provisional observation 'null_item' was accepted:
semantic-empty provisional observation 'empty_map' was accepted:
semantic-empty provisional observation 'empty_string' was accepted:
semantic-empty provisional observation 'nested_substitute' was accepted:
block-style holdout example was ignored:
block-style unknown example was ignored:
incomplete inline example was ignored:
invalid-timestamp example was ignored:
empty source_id was accepted: voice rule V01 example source is unknown: F01
null source_id was accepted: voice rule V01 example source is unknown: F01
duplicate training/holdout source_id was accepted:
null ledger field 'source' was accepted:
null ledger field 'transcript_type' was accepted:
null ledger field 'speaker_exclusions' was accepted:
null ledger field 'word_count' was accepted:
null ledger field 'split' was accepted:
null ledger field 'holdout' was accepted:
EXIT_CODE=1
```

Four focused TDD cycles then reproduced additional fail-open edges before each correction:

```text
semantic-empty provisional observation 'nested_under_record' was accepted:
nested block example fields were accepted as direct fields:
non-list examples content was ignored:
comment-only ledger source was accepted:
```

### Implementation

- Provisional status and observations are recognized only as root keys. An empty rule set requires a real top-level list item with a meaningful scalar observation; null, empty, collection, comment-only, and nested substitutes fail.
- Every `examples` item is parsed fail-closed. Complete inline maps and complete block-style records are supported; malformed timestamps, missing fields, nested substitutes, stray content, unknown sources, and holdout sources fail.
- Source IDs and all required ledger scalars must be semantically non-empty. Duplicate IDs fail, split/holdout values are cross-checked, and the required holdout identity must be distinct from every training support identity.
- The live profile remains unchanged: it is provisional, has no approved voice rules, and contains a real corpus-insufficiency observation.

### GREEN

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
PASS router and voice schema contract
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-package.ps1
PASS package validator
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-package.ps1 -SkillRoot . -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial
Exit code: 0

> python C:\Users\magme\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
Skill is valid!
Exit code: 0

> git diff --check
Exit code: 0
```

Focused results include:

```text
VALID_BLOCK_ERRORS=
NESTED_STATUS=empty voice_rules require profile_status: provisional and non-empty provisional_observations
NESTED_OBSERVATIONS=empty voice_rules require profile_status: provisional and non-empty provisional_observations
BLOCK_HOLDOUT=voice rule V01 example source must be training and holdout false: F03
BLOCK_UNKNOWN=voice rule V01 example source is unknown: F99
INCOMPLETE_INLINE=voice rule V01 contains incomplete example item
INVALID_TIMESTAMP=voice rule V01 example has invalid timestamp: not-a-time
EMPTY_SOURCE_ID=voice source record has empty or null source_id; voice rule V01 example source is unknown: F01
NULL_SOURCE_ID=voice source record has empty or null source_id; voice rule V01 example source is unknown: F01
DUPLICATE_ID=duplicate voice source_id: F01; voice rule V01 example source must be training and holdout false: F01
SCALAR_REJECTED=source:null+empty
SCALAR_REJECTED=transcript_type:null+empty
SCALAR_REJECTED=speaker_exclusions:null+empty
SCALAR_REJECTED=word_count:null+empty
SCALAR_REJECTED=split:null+empty
SCALAR_REJECTED=holdout:null+empty
PASS focused round-2 probes
```

## Task 4 — fix round 1

### RED

Five regression probes were added before changing the parser or source contract.

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
Voice schema regression probes failed:
four-space YAML rule was not validated:
empty non-provisional profile was accepted:
unknown example source was accepted:
holdout example source was accepted:
missing ledger source field was accepted:
EXIT_CODE=1
```

All five probes returned an empty error list under the old validator, reproducing both review findings: indentation-dependent fail-open parsing and no source/holdout integrity check.

### GREEN

The validator now parses YAML list records from their actual indentation, rejects non-empty unparsed rule records, requires an explicit provisional contract when `voice_rules` is empty, validates complete ledger records, resolves every example source, and allows only `split: training`, `holdout: false` examples.

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
PASS router and voice schema contract
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-package.ps1
PASS package validator
Exit code: 0

> powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-package.ps1 -SkillRoot . -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial
Exit code: 0

> python C:\Users\magme\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
Skill is valid!
Exit code: 0
```

Focused probe output:

```text
FOUR_SPACE_ERRORS=voice rule V04 missing required field: counter_evidence
EMPTY_PROFILE_ERRORS=empty voice_rules require profile_status: provisional and non-empty provisional_observations
UNKNOWN_SOURCE_ERRORS=voice rule V01 example source is unknown: F99
HOLDOUT_SOURCE_ERRORS=voice rule V01 example source must be training and holdout false: F03
LEDGER_FIELD_ERRORS=voice source F01 missing required field: source
UNPARSED_RULE_ERRORS=voice_rules contains non-empty unparsed records
```

A fully valid four-space rule produced zero errors. Mutation probes removed each ledger field (`source_id`, `source`, `transcript_type`, `speaker_exclusions`, `word_count`, `split`, and `holdout`) in turn; every mutation was rejected. The live profile remains `profile_status: provisional` with `voice_rules: []` and non-empty `provisional_observations`.

The first two GREEN attempts exposed PowerShell harness errors (`-split` parsed as a named parameter, then an empty trailing line rejected by parameter binding). Both were corrected before the contract produced a passing result.

## Task 4 — fix round 3

Baseline: `aff582b`. The exact review mutations were added before implementation changes.

### RED

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
Voice schema regression probes failed:
OBS_EMPTY_LITERAL=empty block scalar observation was accepted
OBS_EMPTY_FOLDED=empty block scalar observation was accepted
INLINE_NESTED_FIELDS=nested inline-map fields were accepted:
TIMESTAMP_BAD_SECONDS=03:99 was accepted:
source_NULL_COMMENT=semantic-empty ledger value was accepted:
source_EMPTY_COMMENT=semantic-empty ledger value was accepted:
source_EMPTY_BLOCK=semantic-empty ledger value was accepted:
transcript_type_NULL_COMMENT=semantic-empty ledger value was accepted:
transcript_type_EMPTY_COMMENT=semantic-empty ledger value was accepted:
transcript_type_EMPTY_BLOCK=semantic-empty ledger value was accepted:
speaker_exclusions_NULL_COMMENT=semantic-empty ledger value was accepted:
speaker_exclusions_EMPTY_COMMENT=semantic-empty ledger value was accepted:
speaker_exclusions_EMPTY_BLOCK=semantic-empty ledger value was accepted:
word_count_NULL_COMMENT=semantic-empty ledger value was accepted:
word_count_EMPTY_COMMENT=semantic-empty ledger value was accepted:
word_count_EMPTY_BLOCK=semantic-empty ledger value was accepted:
ID[|]=semantic source ID was accepted:
ID[>]=semantic source ID was accepted:
ID[null # semantic-null]=semantic source ID was accepted:
ID[F01 # semantic-duplicate]=semantic source ID was accepted:
EXIT_CODE=1
```

The failures are contract failures, not harness or syntax errors: each mutation reached the real schema validator and was accepted by the `aff582b` implementation.

### Implementation

- Added dependency-free scalar normalization that strips inline YAML comments only outside quotes, recognizes semantic null/empty values, and evaluates literal/folded block content using its indentation context.
- Source IDs and required ledger fields now use the normalized scalar result. Duplicate IDs, source lookup, and the separate holdout requirement compare normalized identities.
- Replaced whole-string inline-map regex searches with a quote- and depth-aware top-level map parser. Nested metadata keys cannot stand in for direct example fields, while complete direct inline and block examples remain supported.
- Timestamp validation now checks component ranges: seconds must be `00`-`59`, as must minutes in `HH:MM:SS`.

### GREEN

```text
> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-router.ps1
PASS router and voice schema contract

> powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\test-package.ps1
PASS package validator

> powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-package.ps1 -SkillRoot . -AllowPlannedMissingModules
PACKAGE_OK C:\Projects\Video\.agents\skills\youtube-editorial

> python C:\Users\magme\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
Skill is valid!

> git diff --check
GREEN_CODES router=0 package=0 staged=0 quick=0 diffcheck=0
```

Focused semantic controls also returned `PASS focused YAML scalar/map/timestamp controls`: quoted `#` content was preserved while an outside comment was removed, a non-empty folded scalar stayed valid, nested flow-map fields stayed nested, quoted commas/braces remained intact, and `03:60`, `03:99`, and `00:60:00` were rejected.

All prior Task 4 controls remain in the same router suite. The live voice profile, source ledger, and valid/invalid fixtures were not changed.
## 2026-08-02 — Lean V1 completion

After Artur requested strict budget conservation, the remaining V1 modules were completed directly without additional model-run evaluation loops.

```text
tests/test-router.ps1          PASS router and voice schema contract
tests/test-package.ps1         PASS package validator
tests/test-script-validator.ps1 PASS script validator
scripts/validate-package.ps1 . PACKAGE_OK
quick_validate.py .            Skill is valid!
Claude junction validation     PACKAGE_OK
```

Runtime validation is dependency-free and read-only. Behavioral multi-run acceptance remains a later optional evaluation, not a claim of completion.
