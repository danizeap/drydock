# Decision Log

## Change

gate-rescopes-2025

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-09 | Bundle the remaining strongly-sourced gate re-scopes into one packet | Same change shape (framework prose), same evidence source, same faithfulness discipline; one verifier + one release is economical and the Owner asked to proceed through the roadmap | One packet per gate (rejected: 4–5x the ceremony for prose edits); the big-bang v0.4 packet including Gate 15 (already declined earlier in favor of Gate-15-first) |
| 2026-07-09 | Re-scope in place; do NOT renumber or add a 23rd gate for CI/CD or fail-open | Preserves the stable 22-gate numbering that the applicability templates, CLI, and every project record depend on; matches the Gate 15 precedent | New Gate 22 "CI/CD Integrity" and Gate 23 "Fail-Open" (rejected: renumbering churn across templates + the CLI's presence checks; CI/CD is a supply-chain sibling and belongs in Gate 10) |
| 2026-07-09 | Fold CI/CD integrity into Gate 10, not a standalone gate | The 2025 incidents (tj-actions, Shai-Hulud runner persistence) are supply-chain compromises of build-time dependencies — the same concern Gate 10 owns, one level out from package deps | Standalone CI/CD gate (rejected: renumber); leaving it uncovered (rejected: named CISA incidents) |
| 2026-07-09 | Frame every claim to the STRONGLY-SOURCED tier, not the confirmed tier | The Gate 15 verifier's lesson: faithfulness is the highest bar for a security spec. These findings have authoritative primary sources (CISA/OWASP/Wiz/Unit42) but their 3-vote adversarial pass was cut off — so cite the incident, calibrate the language, and never assert with Gate-15 confidence | Presenting them as equally confirmed (rejected: overclaim — the exact failure the verifier exists to catch) |
| 2026-07-09 | Bar the REFUTED "1 in 9 / 11.04%" BaaS statistic; cite the phenomenon only | It was killed 0-2 in verification; the RLS-off breach class is real and multiply-reported (Lovable, Tea app) but that specific number did not survive | Citing the number (rejected: it is refuted in our own research note) |
| 2026-07-09 | No recordable applicability sub-blocks (unlike Gate 15's lethal_trifecta) | Gate 15 warranted a structured block because it is a combination check; supply-chain/RLS/webhook are checklist scopes — structured fields would add template surface without adding a combination to record | Adding structured blocks to Gate 10/6/16 (rejected: unwarranted surface; the CLI packet can add detection later) |
