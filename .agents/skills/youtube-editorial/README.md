# youtube-editorial

Local editorial system for creating and revising Russian YouTube scripts. It turns an idea, references, research, Canvas data, an outline, or an existing script into a sourced structure, spoken draft, audit trail, and human-approved production handoff.

## Typical requests

- "Собери структуру ролика из этой идеи и исследований."
- "Напиши полный разговорный сценарий; Canvas нет."
- "Проверь этот сценарий на голос Артура и удобство произнесения."
- "Внеси мои правки после чтения вслух и верни на проверку."
- "Сценарий утверждаю — подготовь visual pack и design handoff."

Canvas is optional. The skill asks one focused question only when an undiscoverable choice materially changes the video; reversible gaps become labeled assumptions.

## Outputs

- `SCRIPT.md` — clean teleprompter text;
- `SCRIPT-NOTES.md` — beat, source, timing, and display notes;
- `SCRIPT-AUDIT.md` — findings and Artur feedback;
- `REFERENCES.md` — claim-level evidence ledger;
- `VISUAL-PACK.md` and `DESIGN.md` — created only after explicit approval.

Statuses: `draft`, `structure_review`, `editorial_review`, `human_review_required`, `approved_by_artur`. Only Artur can set the final status.

## Boundaries

V1 is local and dependency-free. It installs no hook or plugin, makes no runtime network call, and does not record, subtitle, render, edit, create thumbnails, or upload. Those actions remain with the owners in `Video/AGENTS.md`.

## Validation

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test-package.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test-router.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test-script-validator.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-package.ps1 -SkillRoot .
```

Canonical path: `C:\Projects\Video\.agents\skills\youtube-editorial`.
Claude Code path: `C:\Projects\Video\.claude\skills\youtube-editorial` (directory junction to the canonical path).

To remove only the Claude junction after verifying it is a junction:

```powershell
Remove-Item -LiteralPath C:\Projects\Video\.claude\skills\youtube-editorial
```

No global installation is performed.

