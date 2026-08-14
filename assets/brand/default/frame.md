---
name: Immersive Mono
version: 1.0
colors:
  ink: "#0B0B0C"
  paper: "#FAFAF7"
  surface: "#1A1B1D"
  surfaceRaised: "#212225"
  cardDark: "#161618"
  cardDarkBorder: "#2A2A2C"
  secondaryText: "#B7B7B2"
  labels: "#8A8A85"
  dividerDark: "#3A3B3E"
  dividerLight: "#E0E0DB"
  accentHype: "#FF5B2E"
  accentDanger: "#FFC53D"
  accentInsight: "#5BD1FF"
  captionAccent: "#FFD700"
  captionScrim: "rgba(8, 9, 10, 0.52)"
  insertAccentOnPaper: "#E8590C"
typography:
  sans:
    family: "Golos Text"
    weights: [400, 500, 600, 700, 800, 900]
  mono:
    family: "JetBrains Mono"
    weights: [400, 500, 700, 800]
  serif:
    family: "Playfair Display"
    weights: [500, 600, 700]
spacing:
  canvas: [1920, 1080]
  sideMargin: 104
  captionBaseline: 900
  playerZoneStarts: 934
  horizontalSafeZones:
    topBand: [0, 250]
    faceZone: [250, 768]
    accentBand: [768, 934]
    playerZone: [934, 1080]
  vertical:
    canvas: [1080, 1920]
    sideMargin: 72
    rightUiWidth: 180
    topBand: [0, 220]
    accentBand: [1150, 1500]
    bottomUiZone: [1500, 1920]
    typeScale: 1.3
    maxWordsPerPlate: 3
components:
  corners: "sharp unless a source screenshot is presented as a card"
  borders: "hairlines and 4 px accent strips; no decorative outlines"
  shadows: "only for source cards and caption readability"
  accents: "color carries category, never ordinary text"
  sourcePolicy: "prefer alpha overlays; replacing useful source requires explicit approval"
motion:
  enter: "cubic-bezier(0.33, 1, 0.68, 1)"
  transition: "cubic-bezier(0.45, 0, 0.2, 1)"
  constraints: "one movement per element; no spring or bounce"
---

# Immersive Mono frame system

## Overview

This is the HyperFrames-native visual source of truth for the bundled default
brand. Exact visual values live in the frontmatter. `tokens.css` is its runtime
CSS projection; `build_catalog.py` checks that the two do not drift.

The system is monochrome and editorial. Paper and ink carry almost every frame;
the three semantic accent colors are scarce category signals for hype, literal
risk, and insight. They are not a general palette.

## Composition rules

- Preserve useful footage. Prefer an alpha overlay or a true split before an
  opaque full-frame interruption.
- Text must add information or structure. It is never decorative filler.
- A real chapter boundary may use one transition family per video.
- On-screen list items begin on their matching spoken cues, not on a decorative
  fixed stagger.
- The light side-panel agenda is the default hook-plan treatment. The outlined
  process rail is situational inside the body.

## Ownership boundary

This file owns appearance. `usage-profiles.json` owns when a graphic is useful;
`brand-manifest.json` owns ChatMonteur's enforceable budgets and cue contract;
`channel.json` owns public CTA identity; `sound.json` owns sound policy.
