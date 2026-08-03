# ADR-0004: Borrowing charter — look, don't copy

Status: accepted (2026-07-20, decision D4)

## Context

OpenMontage (AGPL-3.0) is the closest prior art and a rich source of hard-won
techniques. We are MIT; AGPL text cannot enter this tree. Ideas, algorithms,
thresholds and prose-restated rules are not copyrightable; source text is.

## Decision

Studying any copyleft/unlicensed project is allowed and encouraged; copying
its code is forbidden. Techniques are restated in our own words from our own
practice, with the source cited in the audit notes. Every third-party licence
is verified against the actual LICENSE file (via `gh api`), never from memory.
Known trap recorded once: Ultralytics YOLO is AGPL — never even a dependency.

## Consequences

Slower than forking, legally clean forever. `_audit/` (gitignored) holds the
provenance of every borrowed idea.
