# Brief

## Change

gate-rescopes-2025 (v0.4.1) — align the remaining gates to the 2024–2026 threat landscape.

Intake: Mode FULL (security-framework change). Primary skill: launchguardian. Spec/standard editing, no code. Approvals: the v0.4 direction is Owner-approved ("do all the next steps"). Evidence base: `sdd-plus/specs/launchguardian-v0.4-gap-research.md`, the STRONGLY-SOURCED tier (primary sources — CISA, OWASP, Wiz, Unit42 — whose 3-vote adversarial pass was cut off by session limits; NOT the [3-0]-confirmed Gate 15 tier). Faithfulness rule for this packet: cite to the primary source, frame to the evidence tier, never assert with the confidence Gate 15's confirmed findings carried. Stop conditions: no renumbering the 22 gates (re-scope in place, per the Gate 15 precedent); no CLI change (parked); no new recordable-field blocks unless a change is genuinely a combination check.

## What this means for your product

The safety review now looks for the attacks that actually hit apps like yours in 2025 — booby-trapped npm packages that run code the moment you install them, hijacked build pipelines, and databases left readable to the public — not just the textbook checklist from a few years ago.

## User Need

The 22 gates were written before the 2025 supply-chain and BaaS-misconfiguration waves. The research surfaced named, primary-sourced incidents that the current one-line gate scopes miss: the Shai-Hulud npm worms (install-script execution, credential theft, self-propagation), the tj-actions CI/CD compromise (mutable action tags, secrets in build logs), slopsquatting (AI-hallucinated package names), the Firebase/Supabase RLS-off breach class (Lovable, Tea app), a Stripe webhook signature bypass, and OWASP Top 10 2025's two new categories (A03 Software Supply Chain Failures, A10 Mishandling of Exceptional Conditions). A non-expert following the gates today can pass every listed item and still ship into these.

## Problem

1. **Gate 10** scopes supply chain as "SBOM + vulnerability thresholds" = known-CVE scanning. The dominant 2025 vector — a freshly-trojanized package running an install script — has no CVE yet, so CVE scanning structurally misses it. CI/CD workflow compromise (mutable Action tags, workflow injection, runner persistence, secrets-in-logs) has no clear home. Slopsquatting (AI-specific) is named nowhere.
2. **Gate 6 / Gate 16** cover object authorization and tenant isolation but do not name the concrete, #1-frequency BaaS failure for this audience: Row-Level Security disabled or the public/anon key readable against unprotected tables.
3. **Gate 13** says "verify webhooks" generically; the concrete failure (empty/missing signing secret → forged webhooks → fraud) isn't named.
4. **Gate 12 / OWASP A10**: fail-open on exceptional conditions isn't called out, though OWASP made it a 2025 top-10 category.

## Scope

In scope (framework spec + standards + scaffold twins; no gate renumbering):

1. **Gate 10 re-scope** — expand the row and add a `## Gate 10 — Supply Chain & CI/CD Integrity` subsection: install-script (pre/post-install) execution as the top real vector; lockfile integrity + pinning; SHA-pinned (not tag-pinned) third-party CI Actions; workflow injection ("pwn requests"), self-hosted-runner persistence, secrets-in-build-logs; slopsquatting (AI-hallucinated package names). Cite Shai-Hulud (CISA 2025-09), tj-actions (CVE-2025-30066), OWASP A03.
2. **Gate 6/16 re-scope** — name the BaaS signature failure concretely: RLS/row-level authorization enabled on every table; the public/anon key cannot read or write what it shouldn't; a privileged service key is never shipped client-side. Cite the RLS-off breach class (phenomenon only — the "1 in 9" statistic was REFUTED, do NOT cite it).
3. **Gate 13** — add: verify the webhook signing secret is present and non-empty; reject unsigned/mis-signed payloads (Stripe CVE-2026-41432).
4. **Gate 12** — add fail-open / exceptional-condition handling (OWASP A10): a failing check must not silently allow the protected action.
5. **Standards** — mirror the new emphases in `security-shipping-standards.md` where the gate list/confirmation lives.
6. Delta spec: ADDED requirements on the `launchguardian` capability for the Gate 10 supply-chain/CI-CD scope and the Gate 6/16 RLS scope (the two load-bearing ones); sync into `capabilities/launchguardian.md`.

Out of scope:

- Recordable applicability sub-blocks like Gate 15's `lethal_trifecta` (these are checklist scopes, not combination checks; adding structured fields is not warranted).
- The CLI (parked: PyPI update is separate).
- Renumbering or adding a 23rd gate (re-scope in place).
- The consequence-approvals work (v0.3.1, next packet).

## Acceptance Criteria

- [ ] Each gate change is faithful to its primary source and framed to the STRONGLY-SOURCED (not confirmed) evidence tier — no overclaim; the REFUTED "1 in 9" statistic absent.
- [ ] Still exactly 22 gates (0–21), no renumbering; gate names unchanged (so the applicability templates stay valid without edits).
- [ ] Every edited file byte-identical to its `assets/project-scaffold/` twin.
- [ ] `check_sync.py` 10/10; full pytest suite unchanged (no code); framework spec and standards internally consistent.
- [ ] Delta spec written and synced; `sdd.py verify`/`archive` gates pass; verifier confirms faithfulness + no gate drift.

## Impact Areas

- Backend/Frontend/Data/API/AI: none in Drydock (governs how agents review a user's project).
- Documentation: LGF framework spec, security-shipping standards (+ scaffold twins), the living capability spec.
- Operations/security: this IS a security-framework change (FULL mode).

## Open Questions

- None blocking. Deferred: recordable supply-chain fields and CLI auto-detection ride the parked CLI packet.
