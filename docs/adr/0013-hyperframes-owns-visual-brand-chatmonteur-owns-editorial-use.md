# ADR 0013: HyperFrames owns visual brand; ChatMonteur owns editorial use

Status: accepted (2026-08-14)

HyperFrames already defines `frame.md` as the frame-scale design system and its
registry as the reusable component mechanism. ChatMonteur therefore does not
create another visual-brand schema: an installed brand uses `frame.md` plus
HyperFrames components. ChatMonteur adds the separate layer HyperFrames does not
provide — brand-neutral editorial intent, brand-specific selection priority,
source-replacement policy, cue budgets, and montage/QC gates. This keeps a new
brand from reimplementing the editor while avoiding two competing sources for
colors and typography.

The `assets/brand/<name>` directory remains a packaging and selection boundary
because ffmpeg-based tools, channel identity, sound policy, and editorial gates
also need the active brand; it is not a replacement for HyperFrames' design spec.
