# Artur voice profile

```yaml
profile_status: provisional
corpus_gate:
  required_transcripts: "3-5 verified solo-video transcripts"
  target_spoken_words: "4000-8000"
  holdout_required: true
voice_rules: []
provisional_observations:
  - observation_id: P01
    status: corpus_insufficient
    observation: "No personal voice rule is approved from the current local corpus."
    evidence: "The ledger contains one timestamped automatic transcript and one recording script; they are not 3-5 independent verified transcripts and do not provide 4000-8000 verified spoken words."
    promotion_gate: "Verify speaker and transcript provenance, add independent timestamped solo transcripts, freeze candidate rules from training sources, then test them against the holdout."
```

`provisional_observations` are corpus notes, not instructions for rewriting. Do not infer slang, fillers, sentence rhythm, humor, pronunciation, or deliberate imperfections from them.
