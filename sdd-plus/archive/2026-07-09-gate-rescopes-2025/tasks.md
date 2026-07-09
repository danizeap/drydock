# Tasks

## Change

gate-rescopes-2025

## Implementation

- [x] Write the delta spec (`specs/launchguardian.md`: ADDED Gate 10 supply-chain/CI-CD requirement + Gate 6/16 row-level-authorization requirement, WHEN/THEN) — before editing.
- [x] Gate 10: expand row + add `## Gate 10 — Supply Chain & CI/CD Integrity` subsection (framework + twin).
- [x] Gate 6/16: expand both rows + add the row-level-authorization (BaaS RLS) note (framework + twin).
- [x] Gate 13 (webhook signing secret) + Gate 12 (fail-open / OWASP A10): one clause each (framework + twin).
- [x] Standards: mirror the supply-chain + RLS emphasis (framework + twin).
- [x] cp root→twin; byte-identity 4/4; `check_sync.py` 10/10; pytest 251 passed / 2 skipped (no code); 22 gates intact, names unchanged; refuted statistic absent.
- [x] Sync the delta into `capabilities/launchguardian.md` (MODIFIED — appended two requirements).
- [x] Run verification: verifier subagent VERIFIED WITH NOTES; both calibration notes (date framing, superlative) resolved; `sdd.py verify` passes.
