# Spoken audit

Review the current Russian script as speech, not as an article. This stage is **audit-only by default**: return findings and do not rewrite the source unless Artur asks.

## Inputs and invariants

Load `SCRIPT.md`, the approved-passage map, and **protected spans**. Preserve facts, certainty, quotations, URLs, product names, numbers, personal experience, deliberate fragments, callbacks, and approved wording. Do not claim to detect authorship.

## Listen for

- breath groups that are too long or split in the wrong place;
- written-language syntax that a speaker will involuntarily simplify;
- clusters that are hard to pronounce at recording pace;
- bureaucratic noun/genitive chains and hidden verbs;
- assistant throat-clearing before the actual point;
- repeated cadence, forced three-part lists, and mechanical contrasts;
- transitions that name the structure instead of moving the thought;
- wording Artur is likely to paraphrase involuntarily during a cold read.

## Finding format

```yaml
- location: B03 / paragraph 2
  excerpt: "Exact short excerpt"
  listening_problem: "What a listener or speaker will experience"
  minimal_repair: "Smallest safe replacement or split"
  severity: P1
```

`P0` blocks meaning or recording; `P1` creates audible friction; `P2` is optional polish. Use **minimal repair**: do not flatten the speaker's rhythm while fixing one sentence. If no material problem exists, report `no_finding` rather than manufacture variation.

