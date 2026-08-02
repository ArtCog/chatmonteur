# Production lifecycle

ChatMonteur closes the video-production loop from editorial development through a QC-approved render. Distribution remains a separate boundary.

## Phase 0: editorial pre-production

The `youtube-editorial` skill owns:

1. intake and project identity;
2. research, sources, and structure;
3. natural Russian spoken-script drafting;
4. spoken, retention, and evidence audits;
5. Artur's cold read and explicit approval;
6. a file-based handoff to recording and montage.

The canonical package is `.agents/skills/youtube-editorial`. Codex and Claude Code discover this same physical directory through local junctions; no runtime-specific skill copy is maintained.

## Per-video contract

Every new project is initialized under `projects/<yyyy-slug>/` with:

- `PLAN.md` as the authoritative entry point, state, decisions, and review log;
- `preproduction/SCRIPT.md` as clean spoken text;
- `preproduction/REFERENCES.md` as the claim-level evidence ledger;
- `preproduction/VISUAL-PACK.md` as the acquisition brief;
- `preproduction/DESIGN.md` for video-specific design exceptions;
- `raw/`, `assets/`, `clips/`, `transcripts/`, `previews/`, `renders/`, and `youtube/` for the production lifecycle.

`canvas.json` is optional. Chat history is never authoritative project state. Local project dossiers are private and ignored by the public repository; the reusable public skeleton lives inside the skill package.

## Visual handoff: two passes

Before recording, `VISUAL-PACK.md` states what evidence, screenshot, screencast, diagram, or connective visual must be obtained and why. Captured files and their project manifest live under `assets/`.

After the meaning cut locks timing, montage creates exact placement in `transcripts/storyboard.json`. Reusable media may be promoted to the shared `bank/`; project-specific media stays in the project.

## Human gate

Only Artur may approve a script. Agents stop at `human_review_required`, accept cold-read feedback, revise, and wait for explicit approval. Montage may not infer approval from a polished draft.

## Legacy pilot

The first behavioral test uses `C:\Projects\Video\2026-grill-me-top-5-skills` in place. The initializer may add missing contract files but must not move, delete, rename, or overwrite existing material. Migrating the old `Video` tree is a separate operation.
