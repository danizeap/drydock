# Verification

## Change

gate-rescopes-2025

## Automated Checks

- [x] Dual-copy byte-identity — framework spec and standards each identical to their `assets/project-scaffold/` twin (diff -q), before and after the fix round. The two applicability YAML templates were not touched and remain in `check_sync` 10/10.
- [x] `python scripts/check_sync.py` — OK 10/10.
- [x] `python -m pytest tests/ -q` — 251 passed, 2 skipped (unchanged; no code touched).
- [x] Gate integrity — 22 gate rows (0–21), no renumbering; every "Gate N — Name" cell unchanged (only description cells edited); the new `## Gate 10` and `## Gates 6 & 16` are markdown subsections, not gate rows.
- [x] REFUTED statistic ("1 in 9 / 11.04% / 20,052") — ABSENT from all reader-facing content (grep 0/0 in framework + standards, root + twins); it appears only as an explicit bar-against-citing in the delta/capability spec.
- [x] `python scripts/sdd.py verify gate-rescopes-2025` — passes after this record is filled.

## Manual Checks

- [x] Faithfulness / evidence-tier calibration (highest bar): every incident-level claim traces to `launchguardian-v0.4-gap-research.md`, and every specific figure the note carries (Shai-Hulud ~500/~700 package counts, tj-actions 23,000 repos) was deliberately OMITTED rather than asserted — calibrated to the STRONGLY-SOURCED (not confirmed) tier. Gate 13 generalized to "signing secret present, non-empty, enforced" without naming the CVE (safe direction).
- [x] Scope — only Gates 6/10/12/13/16 touched; no code, no CLI, no YAML template changes, no new applicability sub-blocks, no consequence-approvals content.
- [x] Cross-references resolve — the "see … below" refs in the Gate 6/10/16 rows point to the actual subsection headings; Gate 6 and Gate 16 both point to the shared "Gates 6 & 16" subsection.
- [x] Delta ⇄ capability — both ADDED requirements present by exact name in `capabilities/launchguardian.md`; the v0.4.0 Gate 15 requirement still present (appended, not replaced).

## Documentation Updates

- [x] README or user-facing docs updated, if needed. (This IS a docs/spec change: framework spec + standards + scaffold twins + capability spec.)
- [x] Project context updated, if needed. (Not needed.)
- [x] Specs updated, if needed. (Framework spec + capability spec.)
- [ ] No documentation update needed. Reason: n/a.

## Independent Review

`drydock:verifier`, faithfulness as the highest bar. **VERIFIED WITH NOTES.** All hard checks passed (incident-level faithfulness with every specific count omitted, refuted statistic absent + explicitly barred, 22 gates intact with unchanged names, dual-copy 10/10, pytest 251/2, delta⇄capability parity with the Gate 15 requirement retained, cross-refs resolve, no scope creep). Two calibration notes — the honest equivalent of the Gate 15 packet's finding — both resolved before archive:

1. **Date framing beyond the evidence** — the Gate 10 subsection said supply-chain compromises "of 2024–2025", but every sourced incident is 2025. **Resolved** → "of 2025" (matching the capability requirement's own wording).
2. **Unearned superlative** — "the most frequent object-authorization failure for BaaS stacks"; its only quantitative basis was the refuted 1-in-9 statistic. **Resolved** → "A common and repeatedly documented object-authorization failure", dropping the superlative while keeping the qualitative, sourced claim.

Re-checked after the fix: framework twin identical, check_sync 10/10, 22 gates intact, both flagged phrases gone.

## Result

PASS. Verifier VERIFIED WITH NOTES; both calibration notes resolved. Faithfully framed to the strongly-sourced evidence tier, refuted statistic barred, 22 gates and their names intact, dual-copy 4/4, suite 251/2 unchanged.
