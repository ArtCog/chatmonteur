# Structure

Create or revise the beat map before spoken prose when structure is absent or materially changing.

If no Canvas or outline exists, output a labelled **provisional structure** only. Retain supplied facts, label assumptions, set status `structure_review` (`needs human outline/review`), and keep it separate from spoken-script text and production planning. Never call it production-ready.

## Beat schema

Use one record per beat:

```yaml
id: B01
purpose: string
say: string
show: string
payoff: string
evidence_refs: [S01]
setup_id: null
closes_setup_id: null
estimated_seconds: 30
```

`say` is a concise content promise, not polished spoken prose. `show` names an existing or candidate proof/demo, not an invented shot. `evidence_refs` must resolve to known source IDs or use an explicit `unverified` marker.

## Structure contract

- Build causal progression: each beat changes what the viewer understands and creates the reason for the next beat.
- Give every setup/open loop a stable `setup_id`; set the closing beat's `closes_setup_id` to it. Report open setups with no planned closure.
- State source status for every factual beat: supported source ID, `experience`, `inference`, or `unverified`.
- Preserve the packaging promise, factual certainty, protected spans, and approved passages.
- Estimate duration beat by beat; label the rate assumption when measured WPM is unavailable.

Reference transcripts are evidence and comparison material, not a substitute for editorial reasoning. Do not stretch one transcript into a new structure. State the independent organizing principle, viewer transformation, and why each beat belongs.

Output the beat map, setup/closure map, total estimated duration, source gaps, provisional assumptions, and status. Wait for structure direction before `draft` when the structure was newly created or materially changed.
