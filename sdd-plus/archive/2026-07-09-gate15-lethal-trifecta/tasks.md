# Tasks

## Change

gate15-lethal-trifecta

## Implementation

- [x] Write the delta spec (`specs/launchguardian.md`, ADDED lethal-trifecta requirement + scenarios) — before editing the specced behavior.
- [x] Framework spec: expand Gate 15 row + add the `## Gate 15 — the Lethal-Trifecta Test` subsection (root + scaffold twin, byte-identical).
- [x] Applicability templates: add the `lethal_trifecta` block to the Gate 15 entry in `gate-applicability.template.yml` and `gate-applicability.output.template.yml` (root + twins).
- [x] Standards: one-line trifecta high-risk note in Gate Confirmation (root + twin).
- [x] Diff every edited pair for byte-identity (4/4 identical); `check_sync.py` 10/10; full pytest suite 251 passed, 2 skipped (no code touched); both YAML templates parse.
- [x] Sync the delta into `sdd-plus/specs/capabilities/launchguardian.md`.
- [x] Run verification: verifier subagent VERIFIED WITH NOTES (faithfulness bar); all four notes resolved (sourced the integration_tokens detail, calibrated read-only, added worked example, reconciled field shape); `sdd.py verify` passes.
