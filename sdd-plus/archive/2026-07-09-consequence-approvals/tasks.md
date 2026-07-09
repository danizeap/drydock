# Tasks

## Change

consequence-approvals

## Implementation

- [x] Write the delta spec (`specs/approvals.md`: ADDED consequence-request + decline-path requirements, WHEN/THEN) — before editing.
- [x] `framework-usage.md` §7: replace the stop format with the two-variant consequence template + protocol + decline path (root + twin, byte-identical). Trigger list and timing paragraphs kept.
- [x] New `sdd-plus/templates/approval-request.md` (FULL + QUICK forms) (root + twin).
- [x] cp root→twin; byte-identity 2/2; `check_sync.py` 10/10; pytest 251 passed / 2 skipped; §8 APPROVE reference intact; marker present.
- [x] Sync the delta into `capabilities/approvals.md`.
- [x] Run verification: verifier subagent VERIFIED WITH NOTES; all four notes resolved (ternary reversibility header, numbered-parts, casing, check_sync pair 11/11); `sdd.py verify` passes.
