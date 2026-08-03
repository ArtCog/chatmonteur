# ADR-0011: Intelligence is the agent; code only executes

Status: accepted (2026-07-21, decision D11 — after the first dogfood run)

## Context

The first dogfood run exposed the naive meaning-cutter (`cut_meaning.py`,
a filler dictionary plus "no words = cut" logic): it silently removed 28s of
50s, including silent demo footage and speech ASR had hallucinated over.
No detector script can own decisions that require understanding.

## Decision

Every intelligent decision (fillers, retakes, visual plan, cue placement) is
made by the AGENT, written as a reviewable plan artifact (edl.json,
storyboard.json, cue plan), approved by the user, then executed by a dumb,
deterministic tool. `cut_meaning.py` was deleted, replaced by `cut_edl`.

## Consequences

Plan artifacts are the audit trail of every edit. Tools validate plans hard
(ranges, budgets, geometry) but never make editorial choices. New "smart"
features must arrive as agent skills + a dumb executor, not as detectors.
