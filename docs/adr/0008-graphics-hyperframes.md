# ADR-0008: Graphics engine — HyperFrames

Status: accepted (2026-07-20, decision D8)

## Context

Brand graphics (plashkas, callouts, transitions, captions-as-components) need a
motion engine. Remotion's company licence is paid; Manim/Revideo are niche.
HyperFrames is Apache-2.0, agent-native (HTML/GSAP compositions), ships a
registry of 138 ready blocks, and the team already has production experience
with it.

## Decision

All brand graphics render through HyperFrames with alpha, composited onto
footage by ffmpeg. The brandbook is ported as HyperFrames components with a
generated catalog as the agent's inventory.

## Consequences

Rule zero includes our own library: check `catalog.json`, then the HyperFrames
registry, before writing any new graphic. Other engines can arrive later as
plugins, not core.
