# Security policy

## Supported versions

ChatMonteur is currently in the `0.1.x` release series. Security fixes are made
against the latest release and the default branch; older development snapshots
are not supported.

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |
| `< 0.1` | No |

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/ArtCog/chatmonteur/security/advisories/new).
Do not open a public issue for a suspected vulnerability.

Include the affected version and platform, reproduction steps, potential impact,
and a minimal proof of concept when it is safe to provide one. Please remove API
keys, personal media, transcripts, and other private data before attaching logs or
project artifacts.

We aim to acknowledge a report within seven days and will coordinate disclosure
after a fix or mitigation is available. Complex reports may take longer to assess.

Vulnerabilities in ffmpeg, auto-editor, faster-whisper, HyperFrames, or another
upstream dependency should normally be reported to that project. Please also tell
us privately when ChatMonteur's integration makes the issue reachable through its
documented workflow.

## Scope

Relevant reports include, but are not limited to:

- command or argument injection through project data;
- writes outside the selected `projects/<slug>/` container;
- unsafe handling or disclosure of secrets and private media;
- dependency or build-chain weaknesses specific to ChatMonteur;
- bypasses of approval, rights, redaction, or file-quality gates that create a
  security or privacy impact.
