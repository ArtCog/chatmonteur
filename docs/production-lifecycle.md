# Production lifecycle

Public ChatMonteur v0.1 begins at montage ingest and ends at a QC-approved
master. Research, script development, localization, recording, distribution,
and upload may wrap this lifecycle, but they are separate products and are not
bundled with the montage core. See ADR 0012.

## Upstream handoff

ChatMonteur accepts language-neutral production inputs:

- recorded source media;
- an optional transcript and EDL;
- optional visual assets with licence metadata;
- optional cue, storyboard, subtitle, and sound plans.

An upstream editorial system may create these files, but ChatMonteur does not
require a particular research, scripting, language, or publication workflow.

## Per-video contract

Every project lives under `projects/<yyyy-slug>/`:

- `PLAN.md` — current production state and approval decisions;
- `raw/` — immutable imported recordings;
- `assets/` — project media and licence records;
- `clips/` — reproducible technical and editorial intermediates;
- `transcripts/` — ASR, EDL, cue, subtitle, sound, and storyboard plans;
- `compositions/` — project motion sources and renders;
- `previews/` — human approval artifacts;
- `renders/` — mechanical drafts, approved masters, and QC evidence.

`chatmonteur init <yyyy-slug>` creates the contract idempotently.
`chatmonteur edit ... --project <yyyy-slug>` also imports external source media
into immutable `raw/`; existing files are never overwritten.

## Mechanical front door

`chatmonteur edit` runs the unattended mechanical pipeline and writes
`renders/mechanical-draft.mp4`. A passing file gate recommends
`continue_editing`, because technical correctness is not editorial approval.

## Agent-driven finishing

The agent uses `chatmonteur run <capability> --params <run.json>` for the
meaning cut, privacy redaction, visual pass, subtitles, transitions, sound,
final render, and QC. The required human gates live in `skills/montage.md`.

A technically healthy internal master with unresolved media rights reports
`review_rights`. Only a rights-cleared master may report `ship`.

## Distribution boundary

Descriptions, thumbnails, upload credentials, scheduling, and platform upload
are deliberately outside the public v0.1 montage contract.
