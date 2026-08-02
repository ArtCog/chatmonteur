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
C:\Projects\.agents\skills\youtube-editorial          # Codex junction
C:\Projects\.claude\skills\youtube-editorial          # Claude Code junction
```

The old `Video` paths remain untouched until a separate migration is designed and approved. No duplicate skill copy is allowed.

## Per-video contract

Every future video lives under `C:\Projects\chatcut\projects\<yyyy-slug>\`. Pre-production and montage share the same project root:

```text
projects/<yyyy-slug>/
  canvas.json               # optional planning UI state
  SCRIPT.md                 # clean spoken text + editorial status
  SCRIPT-NOTES.md           # beats, sources, visuals, timing
  SCRIPT-AUDIT.md           # findings and Artur feedback
  REFERENCES.md             # claim-level evidence ledger
  VISUAL-PACK.md             # post-approval capture/create checklist
  DESIGN.md                  # per-video direction; links shared brand system
  raw/                       # immutable source recordings
  clips/                     # montage intermediates
  transcripts/              # ASR, EDL, storyboard
  previews/                  # review renders
  renders/                   # final outputs and QC evidence
```

Canvas is optional. Files are authoritative; chat history is not. Existing ChatMonteur folder conventions remain valid.

## Agent routing

- Root `AGENTS.md` and `CLAUDE.md` route any video idea, structure, script, or script review to `youtube-editorial`.
- Chatcut `AGENTS.md` and `CLAUDE.md` define it as Phase 0 before recording and montage.
- Both agents use the same physical skill and project files.
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

## Non-goals for this integration

- deleting or relocating the old `Video` tree;
- automating recording;
- publishing or uploading;
- changing ChatMonteur montage mechanics;
- global installation outside `C:\Projects`.
