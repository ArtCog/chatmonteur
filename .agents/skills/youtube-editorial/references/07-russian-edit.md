# Russian editorial audit

Apply a narrow Russian-language pass after the spoken audit. It is audit-only by default and uses the same finding schema: `location`, `excerpt`, `listening_problem`, `minimal_repair`, `severity`.

## Review scope

- grammar, agreement, government, capitalization, and false homophones;
- punctuation, quotations, abbreviations, ranges, and number consistency;
- pleonasms, bureaucratese, nominalizations, passive constructions, and vague qualifiers;
- clarity for the intended audience without erasing technical precision;
- false positives: fragments, repetitions, pauses, callbacks, and register choices may be intentional spoken devices.

## Safety rules

Respect protected spans and Artur's explicit choices. Normative em dashes are valid Russian punctuation. Preserve spoken rhythm when formal normalization would make the line harder to say. Do not impose typography that is useful for print but invisible or disruptive in a teleprompter. Do not optimize for an authorship classifier or add decorative slang, metaphors, or emotion.

For each problem, propose the smallest correction that preserves meaning and certainty. Separate an objective language error from a discretionary style suggestion. Apply changes only when Artur asks for revision.

This module is a narrowed adaptation of `talkstream/ru-text` v2.0.1. Provenance and exclusions are recorded in `UPSTREAM.md`.

