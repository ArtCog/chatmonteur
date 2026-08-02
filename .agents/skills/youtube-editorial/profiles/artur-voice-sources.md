# Artur voice source ledger

The local inventory is insufficient for approved voice rules. Paths below are read-only candidates; local presence does not by itself prove speaker identity, solo status, transcript accuracy, or publication state.

```yaml
sources:
  - source_id: A01
    source: "C:\\Projects\\Video\\_archive\\2026-glm-claude-code\\renders\\master_nomusic_transcript.json"
    transcript_type: "automatic transcript with segment timestamps"
    speaker_exclusions: "No exclusions verified; confirm that all 185 segments are Artur before training use."
    word_count: 1593
    split: training
    holdout: false
    verification_state: candidate_needs_speaker_and_transcript_verification
  - source_id: A02
    source: "C:\\Projects\\Video\\_archive\\2026-fable-opus-sonnet-test\\youtube\\SCRIPT-8-10-MIN-RECORDING.md"
    transcript_type: "recording script with section time ranges; not a verbatim recording transcript"
    speaker_exclusions: "Bracketed stage directions and headings are non-spoken; actual delivery is unavailable."
    word_count: 1958
    split: holdout
    holdout: true
    verification_state: candidate_not_eligible_until_matched_to_recorded_delivery
```

## Holdout protocol

1. Verify provenance, speaker identity, transcript type, speaker exclusions, and spoken-word count before a source becomes eligible.
2. Keep the holdout out of rule discovery and example selection.
3. Derive candidate rules only from at least two different eligible training source IDs, each with a timestamped excerpt.
4. Freeze candidate wording, scope, and confidence before examining the holdout.
5. Use the holdout only to confirm, narrow, lower confidence, or reject a frozen rule. Never use it to manufacture the second supporting example.
6. Record counter-evidence even when it weakens a preferred rule.

Do not upload unpublished transcripts or excerpts to any network service. Add sources by local path when publication or sharing permission is unclear.
