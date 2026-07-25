# LaunchGuardian Finding Triage

Date: 2026-07-25
Scan: `launchguardian scan --target . --framework-mode --strict-scanners`
Observed verdict: **APPROVED_WITH_DISPOSITIONS** — 6 High findings retained,
0 open blocking findings

This document classifies reachability and records the Owner-approved,
evidence-backed disposition. It does not suppress, delete, or reduce the
severity of any scanner finding. Each result retains `severity: high` and its
original `blocks_launch: true`; exact reviewed status `not_applicable` makes it
non-open. The result is deliberately not plain `APPROVED`.

## Findings

| Findings | Triage | Evidence | Safe disposition |
| --- | --- | --- | --- |
| Four Python-3.6 compatibility findings in the new Codex `Popen` calls | Scanner-policy mismatch, not a reachable compatibility defect | Drydock's declared floor is Python 3.9+ in `PROJECT_CONTEXT.md`, `AGENTS.md`, and `README.md`; readiness blocks Python below 3.9; CI runs 3.9 and 3.12. The flagged `encoding`/`errors` parameters exist in every supported runtime. | Owner-approved `not_applicable` disposition for the two exact rule IDs. Findings remain visible and High; no wildcard, path exclusion, or inline scanner ignore is used. |
| Two identical Python-3.6 compatibility findings in legacy `scripts/conductor/codex_bridge.py` | Same scanner-policy mismatch | Same Python 3.9+ floor; the current legacy suite returns 548 passed and 6 skips. | The same exact rule-level disposition applies. Code is not rewritten to emulate an excluded runtime or churn the protected legacy surface. |

## Resolved Since The Prior Scan

The reachable legacy `subprocess.run(..., shell=True)` finding is absent from
the current strict report. The separately approved
`privileged-test-runner-hardening` packet replaced implicit-shell execution
with a precompiled absolute-argv plan, refused worker-writable temporary
executables, and routed every approved step through a pinned, model-free Codex
sandbox. The live Windows boundary denied out-of-worktree writes, descendant
writes, direct sockets, and common secret-bearing environment variables. Host
filesystem read isolation remains explicitly unestablished; this is not
recorded as a full-isolation claim.

The mutable GitHub Action references are now pinned to full, verified commits:
`actions/checkout` v4.4.0 at
`11d5960a326750d5838078e36cf38b85af677262` and
`actions/setup-python` v5.6.0 at
`a26af69be951a213d495a4c3e4e4022e16d87065`. The historical WebSocket
observation remains in the vision spec, but the non-executable prose no longer
contains a scanner-triggering plain-scheme literal. The strict scan at
`2026-07-25T14:03:54.497175Z` confirms all three findings are absent.

## Reviewed Disposition Mechanism

The companion `launchguardian-cli` commit
`24abba5c9cd3eb723356e7ec0de640b7c8278680` on branch
`codex/reviewed-finding-dispositions` implements exact Semgrep rule-ID
matching. It requires `status: not_applicable`, non-placeholder reason and
evidence, a named approver, and a non-future ISO approval date. Wildcards,
duplicates, malformed records, and Critical matches fail closed. Unmatched
entries remain visible as stale-review findings.

That source branch also pins external-scanner subprocess text and Python child
environments to UTF-8. Its suite returns 80 passed, package build succeeds, and
a strict self-scan completes. The Drydock strict scan at
`2026-07-25T15:16:29.577002Z` reports all five scanners `ran`, 6 raw Semgrep
results, 0 raw Semgrep errors, 6 applied dispositions, and 0 open blockers.
Approver text is auditable repository evidence, not authenticated proof of
identity.

## Owner Decisions Needed Before Release

1. Complete the Codex-host final independent review.
2. Merge, version, and publish the reviewed LaunchGuardian change before
   expecting installed `launchguardian` commands or CI to reproduce this
   source-build result.

Until those steps and end-to-end dogfooding are complete, the Codex host
implementation may be tested locally but SHALL NOT be published as
release-ready.
