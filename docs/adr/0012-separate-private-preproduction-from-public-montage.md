# ADR 0012: Separate private preproduction from the public montage core

Status: accepted (Artur, 2026-08-12)

## Context

Artur's workspace includes an editorial preproduction system for ideas, research,
evidence, Russian spoken-script adaptation, cold reads, and YouTube packaging.
ChatMonteur's public promise is autonomous professional montage. Coupling both
systems would ship personal workflow and Russian-specific material as mandatory
product structure, blur the release boundary, and imply multilingual script
capabilities that v0.1 does not provide.

## Decision

Public ChatMonteur v0.1 begins at montage ingest. Its per-video contract contains:

- `PLAN.md` for montage state and approval decisions;
- `raw/`, `assets/`, `clips/`, `transcripts/`, `compositions/`, `previews/`, and `renders/`.

The public interchange is language-neutral: media plus transcript, EDL, cue plan,
and storyboard data. Public templates and documentation are English-first.

Artur keeps the broader private workspace wrapper with `preproduction/`, research,
Russian voice adaptation, and `youtube/`. That wrapper may hand assets and approved
text into the montage contract, but it is not required by or bundled as the public
v0.1 workflow. Other languages may be added later as optional editorial packs,
without changing the montage core.

## Consequences

- `chatmonteur init` and `chatmonteur edit` create only the public montage contract.
- The private `youtube-editorial` initializer may create the superset non-destructively.
- Release packaging must exclude private voice profiles, personal research, and
  locale-specific editorial rules unless they are deliberately published as a
  separate optional package.
- Montage remains usable with Russian or any other language because its file
  formats do not encode a language-specific workflow.
