# LaunchGuardian Finding Triage

Date: 2026-07-25
Scan: `launchguardian scan --target . --framework-mode --strict-scanners`
Observed verdict: **BLOCKED** — 6 high/blocking, 0 non-blocking

This document classifies reachability; it does not waive, suppress, downgrade,
or close any scanner finding. Launch remains blocked until remediation,
launch-scope removal, or an Owner-approved exception is recorded through the
LaunchGuardian process.

## Findings

| Findings | Triage | Evidence | Safe disposition |
| --- | --- | --- | --- |
| Four Python-3.6 compatibility findings in the new Codex `Popen` calls | Scanner-policy mismatch, not a reachable compatibility defect | Drydock's declared floor is Python 3.9+ in `PROJECT_CONTEXT.md`, `AGENTS.md`, and `README.md`; readiness blocks Python below 3.9; CI runs 3.9 and 3.12. The flagged `encoding`/`errors` parameters exist in every supported runtime. | Do not rewrite working subprocess I/O merely to support an excluded runtime. Resolve through a LaunchGuardian/Semgrep rule-profile fix or an explicit evidence-backed Owner disposition. Until then the scanner remains blocking. |
| Two identical Python-3.6 compatibility findings in legacy `scripts/conductor/codex_bridge.py` | Same scanner-policy mismatch | Same Python 3.9+ floor; the current legacy suite returns 548 passed and 6 skips. | Same as above. This is also outside the additive Codex adapter boundary, so code churn would violate the protected-surface constraint without improving supported-runtime security. |

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

## Scanner Configuration Limitation

The installed LaunchGuardian 0.2.0 discovers `launchguardian.yml` and reports
configured exclusions, but its Semgrep adapter invokes:

```text
semgrep scan --config auto --json --output <report> <target>
```

The adapter does not pass `LaunchGuardianConfig` exclusions to Semgrep or
post-filter normalized Semgrep findings. Therefore adding
`exclude.paths`/`exclude.globs` would make the report *look* configured without
resolving these external-scanner findings. No such misleading configuration
was added.

Semgrep-specific ignores could hide entire files, including real findings, and
are not an acceptable automatic response. A rule-level supported-runtime
profile or reviewed finding-disposition mechanism belongs in
`launchguardian-cli`.

## Owner Decisions Needed Before Release

1. Decide whether to extend `launchguardian-cli` with a rule-level
   supported-runtime profile or reviewed per-finding disposition mechanism
   (recommended), or explicitly authorize repository-local suppression of the
   six compatibility findings.
2. Complete the Codex-host final independent review.

Until those decisions and the final independent review are complete, the Codex
host implementation may be tested locally but SHALL NOT be published as
release-ready.
