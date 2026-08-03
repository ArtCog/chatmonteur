# ADR-0010: Name — ChatMonteur

Status: accepted (2026-07-20, decision D10)

## Context

The working title "chatcut" collided with existing tools and undersold the
scope. "Monteur" (монтажёр) names the profession the product replaces —
the film editor — and the "Chat" prefix names the interface: you talk to it.

## Decision

The product and repo are **ChatMonteur** (github.com/ArtCog/chatmonteur; the
old repo name redirects). The local folder may lag until no session holds it
open.

## Consequences

All public naming uses ChatMonteur. Internal paths may still read `chatcut`
until the folder rename lands with v0.1.
