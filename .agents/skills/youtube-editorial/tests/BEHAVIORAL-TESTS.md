# Behavioral tests

Run each case in a fresh context only when evaluating a release. Raw outputs remain immutable.

| Case | Allowed modules | Expected output | Prohibited side effects | Terminal status |
|---|---|---|---|---|
| Canvas input | 01–04 | sourced structure and draft | rewriting Canvas fields outside scope | editorial_review |
| No Canvas | 01–04 | provisional structure without blocking | invented specifics | editorial_review |
| Structure only | 01–03 | beat map and evidence gaps | full prose | structure_review |
| Voice/spoken audit | 05–07 | severity-ranked findings | generic humanizer rewrite | unchanged |
| Protected factual script | 05–08 | byte-preserved spans | changed facts or certainty | human_review_required |
| Human edit and approval | 09 | Artur version as source of truth | agent self-approval | approved_by_artur only after explicit approval |
| Evidence pack | 03,08 | claim-level ledger | invented links | structure_review |
| Production handoff | 10 | VISUAL-PACK and DESIGN | recording/render/upload | approved_by_artur |
| Render/thumbnail/upload request | none | route via Video/AGENTS.md | loading youtube-editorial | unchanged |

For every case record prompt, loaded modules, outputs, model/settings, source hashes, and a pass/fail decision.

