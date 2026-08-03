# ADR-0007: Transcription — free and local by default

Status: accepted (2026-07-20, decision D7)

## Context

"Free by default" is the project's wedge: the core path must work without any
API key. Paid cloud ASR is sometimes more verbatim (which matters for Tier 2
cutting), but making it the default would break the promise.

## Decision

faster-whisper (local, free) is the default transcriber, with hallucination
filtering and a brand-term correction map. Paid backends are opt-in, one flag,
with an honest warning about the trade-off. The tool warns rather than
silently degrading.

## Consequences

Word-timestamp quality is the known weak point of the free path; upgrades
(stable-ts–style alignment) attach here when dogfood shows real drift.
