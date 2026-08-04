# Full spoken draft

Draft only from the accepted beat map and current evidence ledger. Write complete spoken prose: no bullet outline disguised as a script and no missing connective reasoning.

## Draft contract

- Preserve causal progression, packaging promise, beat function, factual certainty, source boundaries, protected spans, and approved passages.
- Never invent a fact, quotation, URL, result, personal action, opinion, or experience. Treat first-person claims as `experience` only when Artur supplied them.
- Keep unsupported claims narrowed, attributed, inferred, or explicitly unverified as directed by `REFERENCES.md`.
- Put only title, minimal section markers, and spoken words in `SCRIPT.md`.
- Put beat IDs, source IDs, timing, delivery notes, demonstrations, visual ideas, and production notes in `SCRIPT-NOTES.md`; never embed them in spoken prose.
- Preserve deliberately supplied punctuation, fragments, callbacks, and restrained tone. Do not add slang, metaphors, or emotional variation merely to sound human.

## Concrete spoken language

- Prefer one idea per sentence and a visible subject doing a clear action. Split a sentence when the listener must hold two subordinate ideas before reaching the point.
- An abstract claim must immediately earn its place with a concrete example, observable consequence, or exact action. If it cannot, cut it.
- Explain a technical term in plain language on first use. Example: do not stop at `TDD`; say that the agent writes a failing check first and then writes code that makes it pass.
- Prefer concrete effects over vague phrases such as "improves interaction quality", "changes the experience", or "is not magic".
- Use metaphors only when they shorten the explanation and map cleanly to the mechanism. Never stack metaphors.
- Read each paragraph as speech. If a natural spoken paraphrase is shorter and keeps the same fact boundary, use the shorter version.

## Duration

When a measured Artur WPM is available, calculate `target_words = target_minutes * measured_wpm`, compare the actual spoken-word count, and report the difference. When it is unavailable, label any planning rate as a provisional assumption; never present it as Artur's measurement. Prefer editing beat allocation over padding prose.

## Output and handoff

Write `SCRIPT.md` and update `SCRIPT-NOTES.md`; leave evidence in `REFERENCES.md`. Set the draft's status to `editorial_review`, not final or approved.

If the requested route continues to `voice`, hand off exactly these inputs to `references/05-artur-voice.md`: current `SCRIPT.md`, `SCRIPT-NOTES.md`, `REFERENCES.md`, protected-span map, approved-passage map, measured WPM or its explicit absence, and unresolved assumptions. Load that module only at the handoff.
