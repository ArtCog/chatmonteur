# Editorial Lifecycle Integration Design

## Decision

Make `youtube-editorial` the pre-production brain of the public ChatMonteur product. Keep one physical, versioned skill package inside `chatcut`; expose that package to Codex and Claude Code across the `C:\Projects` workspace through directory junctions.

## Product lifecycle

```text
idea/research
  -> structure and evidence pack
  -> spoken script and editorial audits
  -> Artur cold read and explicit approval
  -> recording (human + OBS)
  -> ChatMonteur ingest and meaning cut
  -> visual storyboard, sound, render, QC
  -> approved final file
  -> distribution (separate system boundary)
```

`youtube-editorial` owns work through explicit script approval and production handoff. ChatMonteur montage owns recorded media through the final QC-approved render. The handoff is file-based and does not depend on a conversation.

## Canonical locations

```text
C:\Projects\chatcut\.agents\skills\youtube-editorial  # only physical package
C:\Projects\chatcut\.claude\skills\youtube-editorial  # Claude junction inside chatcut
C:\Projects\.agents\skills\youtube-editorial          # Codex junction
C:\Projects\.claude\skills\youtube-editorial          # Claude Code junction
```

The old `Video` project tree remains untouched until a separate migration is designed and approved. The standalone V1 skill repository under `Video/.agents` is a frozen migration source, not an active global installation; all new discovery junctions resolve to the canonical package in `chatcut`.

## Per-video contract

Every future video lives under `C:\Projects\chatcut\projects\<yyyy-slug>\`. Pre-production and montage share the same project root:

```text
projects/<yyyy-slug>/
  PLAN.md                    # authoritative entry point, status and decisions
  canvas.json               # optional planning UI state; create only when used
  preproduction/
    SCRIPT.md               # clean spoken text + editorial status
    REFERENCES.md           # claim-level evidence ledger
    VISUAL-PACK.md           # acquisition intent: what to obtain and why
    DESIGN.md                # video-specific exceptions; brand defaults elsewhere
    research/                # source notes and captured metadata
  raw/                       # immutable source recordings
  assets/                    # project-local screenshots, screencasts and media
  clips/                     # montage intermediates
  transcripts/              # ASR, EDL and final-timing storyboard
  previews/                  # review renders
  renders/                   # final outputs and QC evidence
  youtube/                   # publication package
```

The initializer creates `PLAN.md`, all four `preproduction` documents, and the directories immediately, so agents never guess whether a file is needed. `VISUAL-PACK.md` is the first-pass acquisition brief; it does not contain final timestamps. Actual project assets and their manifest live under `assets/`. Exact placement is authored in `transcripts/storyboard.json` only after the meaning cut locks timing. Reusable promoted media belongs in `bank/`, never in the project template.

Canvas is optional. Files are authoritative; chat history is not. `SCRIPT-NOTES.md` and `SCRIPT-AUDIT.md` are folded into `PLAN.md` rather than becoming extra root documents.

## Agent routing

- Root `AGENTS.md` and `CLAUDE.md` route any video idea, structure, script, or script review to `youtube-editorial`.
- Chatcut `AGENTS.md` and `CLAUDE.md` define it as Phase 0 before recording and montage.
- Both agents use the same physical skill and project files.
- `PLAN.md` is the deterministic first read for every agent entering a video project.
- Only Artur may set `approved_by_artur`.
- Montage cannot start from an unapproved script unless Artur explicitly chooses an exploratory recording workflow.

## Migration boundary

This integration moves only the reusable skill package and adds routing documentation. Moving or deleting `C:\Projects\Video`, old project folders, studio assets, junctions, Canvas data, recording configuration, or distribution services is a separate migration with inventory, mapping, rollback, and verification.

## Verification

1. Validate the package at the canonical and both junction paths.
2. Confirm the junction targets resolve to one physical package.
3. Confirm Codex and Claude routing documents name the same lifecycle and approval gate.
4. Run the deterministic package/router/script tests.
5. Apply the system to `2026-grill-me-top-5-skills` without moving that project yet; compare produced artifacts and collect Artur's cold-read feedback.
6. Continue the same pilot from Claude Code and confirm it reads the same state without creating duplicate files.

## Non-goals for this integration

- deleting or relocating the old `Video` tree;
- automating recording;
- publishing or uploading;
- changing ChatMonteur montage mechanics;
- global installation outside `C:\Projects`.
