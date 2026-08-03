# ADR-0002: Architecture — CLI hands + agent skills head

Status: accepted (2026-07-20, decision D2)

## Context

A pure CLI cannot make editorial judgements; pure agent improvisation is
unreliable at ffmpeg mechanics. OpenMontage independently converged on the same
three-layer split (tools → skills → references), which we read as confirmation.

## Decision

Deterministic mechanics live in code (capabilities: EDL execution, CFR,
loudness, render). Editorial judgement lives in markdown skills (`skills/`)
read by the agent. When skills and code documentation disagree on editing
procedure, the skills win.

## Consequences

Every new feature must pick a side: if it requires taste, it becomes a skill
instruction; if it is mechanical, it becomes a capability. Hybrids split.
