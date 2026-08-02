# Evidence pack

Collect facts after the structure defines what the video must support. For a newly created or materially changed beat map, begin this stage after structure approval.

Create or update the active project's `REFERENCES.md`. Use one entry per factual claim; do not use a source as blanket support for an entire beat.

## Entry contract

Each entry contains:

```yaml
id: S01
beat_or_claim_id: B01/C01
supported_claim: exact claim and certainty boundary
source: URL | local path | null
source_type: primary|secondary|local_data|experience|inference|unverified
confidence: high|medium|low
verification_state: verified|partially_verified|unverified
candidate_use: quotation|screenshot|recording|demo|none
use_note: exact candidate artifact or capture state
```

For `experience`, identify whose experience and where it was supplied. For `inference`, list the premises. A candidate screenshot, recording, or demo is a ledger item, not authorization to capture or produce it.

No-source rule: `source: null` is allowed only with `source_type: unverified` and `verification_state: unverified`. Every other combination requires a URL or local path.

## Evidence rules

- Preserve the exact claim's scope, time, quantity, and uncertainty.
- Prefer a primary source when available; explain reliance on a secondary source.
- A missing or inaccessible source remains `unverified`.
- Never synthesize a URL, citation, quotation, result, or personal experience to fill a field.
- Separate source content from editorial inference.
- Keep research and supplied source files read-only.

Report unsupported claims and the smallest honest draft treatment: omit, narrow, attribute, label as experience/inference, or retain as explicitly unverified. Do not silently turn uncertainty into fact.
