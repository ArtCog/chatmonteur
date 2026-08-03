# ADR-0003: The dogfood gate

Status: accepted (2026-07-20, decision D3)

## Context

Feature lists lie; the only honest detector of paper features is editing a real
video under a real deadline. The founding channel publishes regularly, so the
material supply is built in.

## Decision

The next channel video is edited ONLY through the product, raw footage to
uploaded render. Anything the product couldn't do becomes a roadmap bug —
no side-editing in other tools.

## Consequences

"Done" for any feature means "survived a real edit", not "tests pass".
Release milestones wait for dogfood runs, even when the code is ready earlier.
