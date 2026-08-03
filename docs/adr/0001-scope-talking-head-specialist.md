# ADR-0001: Scope — a talking-head/screencast specialist, not a video factory

Status: accepted (2026-07-20, decision D1)

## Context

OpenMontage (40k★, AGPL) already owns "generate a video from nothing" — stock,
narration, slideshows. Competing there means competing with a head start we
don't have. Our founding user records real footage (talking head + screencast)
weekly and needs an editor, not a generator.

## Decision

ChatMonteur edits REAL recordings: cleanup, meaning-based cutting, captions,
brand graphics, sound, render. No generation from scratch, no stock-first
workflows, no synthetic narration in the core path.

## Consequences

Depth over breadth: every feature is judged against "does it make a real
recording publishable faster". Features that only make sense for generated
video are out of scope by default.
