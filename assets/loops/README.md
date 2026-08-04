# Calm background loops

Own HyperFrames loops for connective stretches — the "motion without information"
layer from `skills/motion.md`. Sources live here (ours, MIT, kilobytes); the rendered
MP4s belong in the asset bank, which is gitignored.

Render one:

```
cd assets/loops/<name> && npx hyperframes render . -o <name>.mp4
```

## The rule these obey

A background must not be readable. No text, no numbers, no protagonist, no HUD —
the eye must be unable to try. Anything with an edge worth focusing on competes with
the voice, and the viewer loses both.

That rule is also why the HyperFrames registry has no loop to borrow: its `vfx-*`
blocks are showcases built AROUND readable content (`vfx-liquid-background` ships a
fintech dashboard floating on the fluid). Strip the content and the block renders
black — the visual interest was the content, not the effect. Measured 2026-08-04.

## calm-field

Three soft luminous fields drifting on brand ink `#0B0B0C`, `sine.inOut`, 12 s, ends
matching starts so it loops seamlessly. A hair of grain keeps the flat gradients from
banding on YouTube's encoder.
