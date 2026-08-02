# Valid voice profile fixture

Synthetic fixture data only; it is not an Artur voice claim.

```yaml
voice_rules:
  - rule_id: V01
    rule: "Use the demonstrated transition only in explanation passages."
    scope: [explanation]
    examples:
      - {source_id: F01, timestamp: "00:42", excerpt: "first fixture excerpt"}
      - {source_id: F02, timestamp: "03:11", excerpt: "second fixture excerpt"}
    counter_evidence: "Absent in the fixture demo passage."
    confidence: medium
    do_not_imitate: "Synthetic caption noise."
sources:
  - source_id: F01
    source: "C:\\fixtures\\F01.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: training
    holdout: false
  - source_id: F02
    source: "C:\\fixtures\\F02.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: training
    holdout: false
  - source_id: F03
    source: "C:\\fixtures\\F03.txt"
    transcript_type: "fixture transcript"
    speaker_exclusions: "none"
    word_count: 100
    split: holdout
    holdout: true
```
