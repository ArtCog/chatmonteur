# Intake and source map

Use this stage to decide what can be done now without manufacturing missing specificity.

## Discovery order

Inspect only available, in-scope inputs in this order:

Canonical discovery order: current_request > project_identity > canvas > approved_state > existing_script > sources

1. `current_request`: Artur's current request, corrections, and requested output.
2. `project_identity`: active project identity and explicit constraints in `README.md` or the request.
3. `canvas`: `canvas.json`, then generated `CANVAS.md`. When they disagree, prefer `canvas.json`; Artur's current instruction still outranks both.
4. `approved_state`: approved passages, status, and decisions in existing `SCRIPT.md`, `SCRIPT-NOTES.md`, and `SCRIPT-AUDIT.md`.
5. `existing_script`: existing outline or partial/full script.
6. `sources`: `REFERENCES.md`, local references, research, transcripts, and supplied summaries.

Do not edit discovered inputs during intake.

## Three-bucket decision

Classify every missing input:

```text
required_now       omission materially changes the video
provisional        reversible assumption, label it and proceed
later              needed only by a later stage
```

Ask exactly one focused question only when a `required_now` choice cannot be discovered. The question must name the decision and why its alternatives materially change the result. Otherwise proceed, listing each provisional assumption and its downstream effect. Do not ask about `later` inputs.

Canvas is optional. Its absence never blocks a structure that can be built provisionally from the supplied idea and sources.

## Protected-span discovery

Create a working protected-span map before revising supplied language. Record the exact bytes, source location, and reason for:

- quotations, URLs, numbers, product names, locked facts, personal experiences, and approved pronunciations;
- Artur-approved passages and explicit project constraints;
- deliberately supplied punctuation, fragments, callbacks/repetitions, stage directions, and stated tone.

Preserve these spans byte-for-byte unless Artur explicitly reopens the specific span. If two protected items conflict, report the exact conflict and stop only the affected edit.

## Intake output

Report: project path or `chat_only`; discovered inputs with source; protected-span map; the three buckets; provisional assumptions; focused question if required; requested deliverable; and recommended next stage. Do not produce a draft during intake.
