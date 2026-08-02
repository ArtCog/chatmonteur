# Artur voice pass

Apply only voice traits supported by verified Artur material. The purpose is fidelity to observable delivery, not generic humanization.

## Evidence gate

Use `profiles/artur-voice.md` together with `profiles/artur-voice-sources.md`. Promote a voice rule only when the corpus contains 3-5 verified solo-video transcripts, ideally 4,000-8,000 spoken words, and the rule has at least two timestamped examples from different training source IDs. Reserve at least one separate source as `holdout: true`; freeze rules before checking the holdout and never derive a rule from the holdout.

If the gate is not met, apply no personal voice rule. Set top-level `profile_status: provisional`, keep at least one semantic non-empty scalar `observation` under top-level `provisional_observations`, state the corpus gap, and preserve the draft's current restrained tone. Empty, null, collection-only, comment-only, nested substitutes, and literal or folded block scalars without content are not observations.

Evidence priority within this pass:

1. Artur's current explicit correction.
2. Protected spans, locked facts, and approved passages.
3. Verified non-provisional profile rules within their declared scope.
4. Narrative function and factual certainty.
5. Spoken clarity and Russian grammar.

## Rule contract

Every non-provisional rule must contain the following fields. In this illustrative schema, `T01` and `T02` mean two different source-ledger records with `split: training` and `holdout: false`; neither may be the reserved holdout.

```yaml
- rule_id: V01
  rule: "Mechanical, observable wording or rhythm rule"
  scope: [explanation, demo]
  examples:
    - {source_id: T01, timestamp: "00:42", excerpt: "short excerpt"}
    - {source_id: T02, timestamp: "03:11", excerpt: "short excerpt"}
  counter_evidence: "Observed exception or none found"
  confidence: high
  do_not_imitate: "Caption noise and accidental stumbles"
```

Use `confidence: high|medium|low`. Apply a rule only in its stated `scope`. A contradictory current instruction, protected span, approved passage, or holdout result blocks automatic application and must be reported.

Validate every `examples` item; never ignore an unsupported, incomplete, or invalid-timestamp item because two other examples are valid. Inline and block-style examples use the same three required direct scalar fields: `source_id`, `timestamp`, and `excerpt`; names inside nested metadata do not satisfy them. Timestamps use `MM:SS` or `HH:MM:SS`, with seconds and the `HH:MM:SS` minute component in the `00`-`59` range.

Every `examples[].source_id` must resolve to a complete source-ledger record with `split: training` and `holdout: false`. Each ledger record must include a unique, non-null source ID plus non-empty scalar source path or URL, transcript type, speaker exclusions, word count, split, and holdout flag. Evaluate scalar content after removing YAML comments outside quotes and after resolving literal or folded block content; compare source identities after the same normalization. Keep at least one separate `split: holdout`, `holdout: true` record with an ID not used by a training source; it may challenge a frozen rule but never support one.

## Profile dimensions

Evaluate only dimensions the corpus can demonstrate: clause and breath rhythm; sentence-length variation; direct address and pronouns; particles, deliberate fillers, self-correction, and transition habits; jargon, anglicisms, and pronunciation; uncertainty and confidence language; humor, examples, analogies, and payoff cadence; characteristic absences. Separate deliberate patterns from recognition errors, edits, and one-off accidents.

## Pass procedure

1. Preserve the protected-span and approved-passage maps byte-for-byte.
2. Select applicable verified rules by scope and confidence.
3. Make the smallest revisions that satisfy those rules without changing facts, beat function, certainty, or duration materially.
4. Report applied rule IDs, skipped rules with reasons, unresolved conflicts, and remaining provisional observations.
5. Return the script to editorial review; this pass cannot approve it.

## Prohibited substitutions

Do not use a generic "casual human" preset. Do not invent slang, filler, jokes, metaphors, emotional variation, personal experience, or forced imperfection. Do not optimize for an AI detector or claim authorship detection. Do not imitate caption noise, transcription errors, false starts, accidental repetitions, mispronunciations, or stumbles.

Keep unpublished transcripts local. Do not upload them to a network service to build, score, or validate the profile.
