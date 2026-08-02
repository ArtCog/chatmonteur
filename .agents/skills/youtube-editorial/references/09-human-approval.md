# Human approval

Allowed editorial states:

`draft` -> `structure_review` -> `editorial_review` -> `human_review_required` -> `approved_by_artur`

**Only an explicit Artur instruction may set approved_by_artur.** An agent, validator, score, successful audit, silence, deadline, or delegated authority cannot set it.

## Cold-read loop

```text
human_review_required
  -> Artur reads aloud
  -> Artur supplies or makes corrections
  -> agent applies a minimal diff to unapproved passages
  -> rerun only affected audits
  -> human_review_required
  -> explicit Artur approval
  -> approved_by_artur
```

Record stumbles, involuntary paraphrases, factual discomfort, and voice mismatch in `SCRIPT-AUDIT.md`. If Artur edits a file manually, his edited version becomes the source of truth. Approved passages are protected until he explicitly reopens them. A request to "continue" or "prepare production" is not approval unless Artur clearly approves the script.

