# Decision Log

## Change

codex-review-command

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-23 | A thin CLI (`review.py`) over the existing `codex_bridge`, not new review logic | The conductor is already built + verified; the command just needs an in-session entry point | Re-implement in the command doc (rejected: no code path, untestable); a full new module (rejected: duplicates the conductor) |
| 2026-07-23 | The command AUDITS Codex's findings; Codex output is never authoritative | The whole value is two frontier models cross-checking — rubber-stamping would defeat it and could pass a wrong finding | Present Codex's output verbatim (rejected: unverified, and Codex lacks wider repo context) |
| 2026-07-23 | Hardened per a live Codex self-review of `review.py` (prompt-injection framing, byte caps, `OSError`→structured) | Dogfooding the command on its own code surfaced real trust-boundary + robustness gaps; fixing them before archive is the point of the loop | Ship the first draft (rejected: Codex flagged real HIGH/MED issues; three fixed, one refined after audit) |
| 2026-07-23 | Guard realpaths in addition to given paths | Cheap mitigation of the symlink-named-benign → secret-content vector Codex flagged, without over-claiming a fix for an exotic local race | Ignore (rejected: cheap to close); content-based scanning (rejected: guard is name-based by design) |
| 2026-07-23 | STANDARD mode, no verifier subagent | Read-only, reuses the FULL-verified conductor + secret-guard; the new surface is a thin, tested wrapper | FULL mode (rejected: no new security surface beyond the already-reviewed conductor) |
