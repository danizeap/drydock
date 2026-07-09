# Plan

## Change

gate-rescopes-2025

## Approach

Same shape as the Gate 15 packet: framework spec + standards editing, dual-copy, no code. Faithfulness discipline is tighter here because the evidence is the STRONGLY-SOURCED tier (primary sources, adversarial vote incomplete) — cite the incident/standard, never overclaim.

1. **Gate 10** (`launchguardian-framework.md` + twin): expand the row; add `## Gate 10 — Supply Chain & CI/CD Integrity` subsection after the Gate 15 subsection. Content: install-script execution is the top real vector (a fresh trojanized package has no CVE — CVE scanning misses it); lockfile integrity + version pinning; SHA-pin third-party CI Actions (not mutable tags); workflow injection / self-hosted-runner persistence / secrets-in-build-logs; slopsquatting (verify AI-suggested package names resolve to real, established packages). Cite Shai-Hulud (CISA alert, Sept 2025), tj-actions/changed-files (CVE-2025-30066, Mar 2025), OWASP Top 10 2025 A03.
2. **Gate 6 + Gate 16** (framework + twin): expand both rows with the BaaS-RLS concrete failure; add a short `## Gates 6 & 16 — Row-Level Authorization (BaaS)` note: RLS enabled on every table; anon/public key cannot read or write beyond policy; service/admin key never shipped client-side. Phenomenon-only citation (Lovable CVE-2025-48757, Tea app) — the "1 in 9 / 11%" statistic was REFUTED and must not appear.
3. **Gate 13** (framework + twin): one clause — verify the webhook signing secret is present and non-empty; reject unsigned/mis-signed payloads (Stripe CVE-2026-41432).
4. **Gate 12** (framework + twin): one clause — fail-open handling (OWASP A10): a failing security check must deny, not silently allow.
5. **Standards** (`security-shipping-standards.md` + twin): mirror the Gate 10 supply-chain emphasis and the RLS note in the Gate Confirmation / high-impact area, briefly.
6. **Delta spec** `specs/launchguardian.md`: two ADDED requirements (Gate 10 supply-chain/CI-CD; Gate 6/16 row-level authorization). Sync into the existing `capabilities/launchguardian.md`.
7. Verify: byte-identity per pair; `check_sync.py`; pytest unchanged; `sdd.py verify`; verifier (faithfulness + evidence-tier framing + no gate drift); sync; archive; release 0.4.1 (Owner-gated).

## Files Expected To Change

- `sdd-plus/specs/launchguardian-framework.md` (+ twin) — Gate 6/10/12/13/16 rows + Gate 10 subsection + Gate 6/16 note
- `sdd-plus/standards/security-shipping-standards.md` (+ twin)
- `sdd-plus/changes/gate-rescopes-2025/specs/launchguardian.md` (delta) → `sdd-plus/specs/capabilities/launchguardian.md` (sync; MODIFIED — appends requirements)
- `CHANGELOG.md` (at release)

## Risks

- **Overclaim on the un-voted tier** — the Gate 15 verifier caught exactly this. Mitigation: every added claim cites a named primary source; language is calibrated (e.g. "the dominant documented vector" not "always"); the refuted statistic is barred.
- **Dual-copy drift** — mitigation: cp root→twin, diff per pair.
- **Gate drift / accidental 23rd gate** — mitigation: subsections are markdown headings, not table rows; verifier + grep confirm 22 gates and unchanged names.
- **Scope sprawl** — five gates touched; mitigation: Gate 10 and Gate 6/16 get real subsections/notes (the load-bearing ones), Gate 12/13 get single clauses; no template structural changes.

## Rollback

Additive prose only. Reverting the framework spec + standards (+ twins) restores prior wording; the capability requirements are removable. No code, no data. `git revert` of the release commit is clean.
