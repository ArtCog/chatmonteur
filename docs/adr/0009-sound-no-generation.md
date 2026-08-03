# ADR-0009: Sound — mix, never generate

Status: accepted (2026-07-20, decision D9)

## Context

Music generation is an expensive race that is not our fight. 90% of a
"professional sound" for talking-head content is a good bed track, ducking
under speech, and a few well-placed SFX.

## Decision

No audio generation. A CC0 pack (curated by the founding user) ships as the
default bed/SFX set; users drop their own files in a folder. Ducking is ffmpeg
sidechain compression; the agent's skill decides which track goes where and
where SFX land. Loudness (−14 LUFS) is set once, at the final render.

## Consequences

Sound quality depends on the pack's curation, not on models or keys. The mixer
validates agent-authored gain plans so SFX can never bury dialogue silently.
