---
name: youtube-editorial
description: Use when a YouTube video needs a new structure or spoken script, or an existing script feels generic, difficult to say aloud, weakly sourced, inconsistent with Artur's voice, or ready for human review.
---

# YouTube Editorial

Use for structure, spoken-script drafting, evidence review, voice revision, and editorial approval. Do not use for rendering, thumbnails, recording, subtitles, upload, or mechanical video editing; route those to the owner named by `Video/AGENTS.md`.

## Route

1. Identify the active `projects/<yyyy-slug>/` project. When Artur explicitly authorizes a legacy-project pilot, use that existing project in place without moving it. If no project exists, work in chat and propose a canonical path before writing files.
2. Read `PLAN.md` as the deterministic first read. Canonical discovery order: current_request > project_identity > canvas > approved_state > existing_script > sources. Apply the six definitions in `references/01-intake.md`. Canvas is optional.
3. Select the smallest stage sequence that produces the requested result. Structure precedes full prose when structure is absent or materially changing. A targeted audit or revision may start at its corresponding stage.
4. Before work, report `stages: [...]` and `loaded_modules: [...]`. Read only the listed module files; add a module only when its stage becomes necessary.

| Stage ID | Module |
|---|---|
| intake | `references/01-intake.md` |
| structure | `references/02-structure.md` |
| evidence_pack | `references/03-evidence-pack.md` |
| draft | `references/04-draft.md` |
| voice | `references/05-artur-voice.md` |
| spoken_audit | `references/06-spoken-audit.md` |
| russian_edit | `references/07-russian-edit.md` |
| retention_evidence | `references/08-retention-evidence.md` |
| human_approval | `references/09-human-approval.md` |
| production_handoff | `references/10-production-handoff.md` |

## Precedence

Resolve conflicts in this order:

1. Artur's current explicit instruction.
2. Locked facts, quotations, URLs, product names, personal experiences, approved pronunciations, and protected spans.
3. Approved passages and explicit project constraints.
4. Verified Artur voice evidence.
5. Narrative function and packaging promise.
6. Russian grammar and spoken clarity.
7. General style or anti-slop heuristics.

Surface an unresolved higher-priority conflict; never average it away.

## Boundaries

Write outputs only inside the active project. Treat source material as read-only unless Artur authorizes its edit. Only Artur can set `approved_by_artur`; automated checks end at `human_review_required`. Never move, delete, or restructure a legacy project during a pilot; initialize missing editorial files non-destructively and preserve its existing layout.
