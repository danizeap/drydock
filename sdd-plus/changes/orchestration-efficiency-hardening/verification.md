# Verification

## Change

orchestration-efficiency-hardening

## Automated Checks

- [ ] Focused controller/evidence tests.
- [ ] Full Codex adapter suite after candidate freeze.
- [ ] Legacy suite after candidate freeze.
- [ ] Root/scaffold, hook, bundle, release-version, packet, and diff parity.

## Manual Checks

- [x] Confirmed both automated code-review attempts exceeded the configured $1
  provider ceiling without a verdict.
- [x] Confirmed each result reported `subtype: error_max_budget_usd` but
  incorrectly returned `workflow.action: continue_codex_only`.
- [x] Confirmed the first outer-shell timeout left the one known peer child
  alive until it was deliberately stopped; no duplicate was launched while it
  remained active.
- [x] Sent the pre-implementation brief, plan, and delta spec to Fable 5 as a
  15,824-byte bounded request before any runtime edits.
- [ ] Peer critique of the pre-implementation architecture. The sole automated
  attempt returned no verdict: after 115 seconds it exited
  `error_max_budget_usd` under a $0.50 ceiling. This is operational evidence,
  not review or convergence.
- [x] Owner-relayed Claude Code architecture review inspected exact commit
  `8d4dd5c` read-only and returned `converged: false` with four blockers. The
  findings are faithfully summarized, not verbatim-preserved, in
  `claude-architecture-review-round-1.json`.
- [x] Round-one blocker remediation is present normatively: fail-closed
  availability allowlist, objective critique trigger, advisory-only downgrade,
  final-fingerprint full suite, clean-tree reuse, no-auto-restart leases,
  cumulative run budget, and screened out-of-tree terminal retention.
- [x] Owner-relayed round-two review inspected exact range
  `8d4dd5c..dd4c9a5`, confirmed every round-one closure, and returned
  `converged: false` with two new anchoring blockers. Its findings are
  faithfully summarized in `claude-architecture-review-round-2.json`.
- [x] Round-two remediation partitions executable/evidence fingerprints,
  retargets the exact predecessor requirement, places novel requirements under
  ADDED, scans ignored loadable paths, defines the multi-invocation run,
  removes FULL self-labelling and advisory gate scope, and enforces expiry on
  read/start.
- [ ] Round-three Claude/Fable review of the revised packet.
- [ ] Independent review of the frozen implementation.

## Documentation Updates

- [ ] Operator guidance updated.
- [ ] Project context updated if the durable defaults change.
- [x] Delta spec written before runtime code.

## Result

ROUND-TWO ARCHITECTURE BLOCKERS REMEDIATED IN SPEC TEXT; IMPLEMENTATION REMAINS
BLOCKED UNTIL ROUND THREE CONVERGES. The small automated plan request still
exceeded its provider ceiling, proving that an input-byte budget alone does not
predict total peer cost.
