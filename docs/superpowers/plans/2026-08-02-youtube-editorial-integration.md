# YouTube Editorial Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one ChatMonteur-owned editorial system discoverable by Codex and Claude Code, then dogfood it on the existing `/grill-me` project without moving that project.

**Architecture:** The working skill package lives at `chatcut/.agents/skills/youtube-editorial`. Directory junctions expose the same physical package to both runtimes. A deterministic initializer creates a shared per-video filesystem contract; the first pilot writes that contract into the existing `Video/2026-grill-me-top-5-skills` folder while ChatMonteur montage remains untouched.

**Tech Stack:** Markdown skills, PowerShell 7/Windows PowerShell, NTFS junctions, Pester-free PowerShell assertions, Git.

## Global Constraints

- Do not modify ChatMonteur montage code, brand components, `PLAN.local.md`, or the other agent's untracked files.
- Do not move or delete `C:\Projects\Video` or the existing `/grill-me` project.
- Keep one active canonical package; the old standalone V1 repository is a frozen migration source.
- Produced script text and user interaction are Russian; package documentation and code are English.
- Only Artur may set `approved_by_artur`.

---

### Task 1: Import the production skill package

**Files:**
- Create: `.agents/skills/youtube-editorial/**`
- Preserve: `C:\Projects\Video\.agents\skills\youtube-editorial/**`

- [ ] Copy the tracked working package without nested `.git`, `.superpowers`, or raw evaluation transcripts.
- [ ] Run the existing package, router, and script-validator tests from the new canonical path.
- [ ] Commit only the imported package and design documents.

### Task 2: Add the deterministic project initializer with TDD

**Files:**
- Create: `.agents/skills/youtube-editorial/tests/test-project-initializer.ps1`
- Create: `.agents/skills/youtube-editorial/scripts/initialize-project.ps1`
- Create: `.agents/skills/youtube-editorial/assets/project-template/**`
- Modify: `.agents/skills/youtube-editorial/tests/test-router.ps1`
- Modify: `.agents/skills/youtube-editorial/SKILL.md`
- Modify: `.agents/skills/youtube-editorial/references/10-production-handoff.md`

- [ ] Add tests asserting the template contract, non-destructive initialization, and explicit authorization for the `/grill-me` pilot.
- [ ] Run the focused tests and confirm they fail because the initializer and pilot authorization are absent.
- [ ] Add the minimal template, initializer, and routing language required to pass.
- [ ] Run the focused tests and then the full deterministic suite.

### Task 3: Expose one package to both agents

**Files:**
- Create junction: `.claude/skills/youtube-editorial`
- Create junction: `C:\Projects\.agents\skills\youtube-editorial`
- Create junction: `C:\Projects\.claude\skills\youtube-editorial`

- [ ] Create junctions pointing to the canonical package.
- [ ] Verify all junction targets resolve to the same physical directory.
- [ ] Validate the package through each discovery path.

### Task 4: Protect private projects and document the lifecycle

**Files:**
- Modify: `.gitignore`
- Create: `docs/production-lifecycle.md`

- [ ] Ignore local `projects/*` dossiers by default while keeping the public template tracked inside the skill.
- [ ] Document Phase 0, the Artur approval gate, the two-pass visual contract, and the montage handoff.
- [ ] Verify no existing tracked project is hidden or removed.

### Task 5: Run the first real pilot on the old path

**Files:**
- Create: `C:\Projects\Video\2026-grill-me-top-5-skills\PLAN.md`
- Create: `C:\Projects\Video\2026-grill-me-top-5-skills\preproduction/**`

- [ ] Initialize the new contract in the existing project without overwriting current files.
- [ ] Record the legacy source paths and current pilot status in `PLAN.md`.
- [ ] Validate the project skeleton and script state.
- [ ] Stop at `human_review_required`; Artur's cold read is the behavioral acceptance test.

