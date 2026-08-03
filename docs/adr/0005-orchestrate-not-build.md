# ADR-0005: Orchestrate mature engines, never build them

Status: accepted (2026-07-20, decision D5)

## Context

Every serious tool in this space (including OpenMontage) wraps the same
engines. Building our own transcriber/renderer/cutter would burn years to
reach parity with maintained projects.

## Decision

Core engines are dependencies: ffmpeg, auto-editor (pause cutting),
faster-whisper (ASR), HyperFrames (graphics). Our own code is orchestration,
correctness rules, and editorial skills. Deleting our code in favour of a
maintained tool is a win.

## Consequences

Rule zero at work: before writing anything, check whether a shipped dependency
already does it (and read its actual `--help`). New dependencies must clear
the licence bar of ADR-0004.
