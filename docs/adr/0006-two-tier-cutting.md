# ADR-0006: Two-tier cutting

Status: accepted (2026-07-20, decision D6; naive pre-pass removed by ADR-0011)

## Context

Pause removal and meaning-based cutting are different problems. Pauses are an
audio-level fact a script can detect; fillers, false starts and retakes require
understanding what was said — ASR mishears brands, and silent demo footage
looks like "nothing happening" to any word-based detector.

## Decision

Tier 1 (dumb): `cut_silence` removes pauses by audio level only (auto-editor).
Tier 2 (smart): the agent reasons over the verbatim word-level transcript,
writes an EDL, and gets user approval before `cut_edl` executes it.

## Consequences

Two audio branches exist for Tier 1 (mixed track vs voice-only track) with
separately locked thresholds. The original naive filler-dictionary pre-pass
was deleted when it cut silent speech (see ADR-0011).
