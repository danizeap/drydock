# Verification

## Change

adaptive-delegation-ledger

## Automated Checks

- [x] `python -m pytest -q` on the three new focused modules: 35 passed on
  Python 3.14.
- [x] The same focused command under `py -3.11`: 35 passed.
- [ ] Python 3.12 focused execution: interpreter is installed, but this local
  interpreter has no `pytest`; command failed before collection and is not
  counted as a pass. CI remains responsible for Python 3.9/3.12 coverage.
- [x] Ledger suite exercised a real two-process concurrent append on native
  Windows and reconstructed two contiguous, hash-linked records.
- [x] `python -m pytest adapters/codex/tests/ -q`: 157 passed, 2 skipped.
- [x] `python -m pytest tests/ -q`: 548 passed, 6 skipped.
- [x] `python scripts/check_sync.py`: all 11 root/scaffold pairs identical.
- [x] `python scripts/sdd.py verify adaptive-delegation-ledger`: artifact
  structure verified; it correctly continued to report pending review tasks
  rather than archive readiness.
- [x] LaunchGuardian source checkout `c754062d`:
  `scan --target . --framework-mode --strict-scanners` returned
  `APPROVED_WITH_DISPOSITIONS`, 6 Python-below-3.6 compatibility findings,
  all covered by the Owner's two exact `not_applicable` dispositions, and no
  open blocking finding.
- [ ] The globally installed PyPI `launchguardian` 0.2.0 is not equivalent to
  that reviewed source checkout: it ignored the disposition configuration,
  reported `BLOCKED`, and its scanner reader emitted a Windows CP-1252 decode
  exception. That run is failed/incomplete evidence, not a security pass.
- [ ] Separate Codex verification did not converge to a usable verdict:
  two `gpt-5.6-sol` runs timed out at 600 and 300 seconds, one
  `codex-auto-review` run correctly returned `BLOCKED` after being prohibited
  from reading, and a final read-only inspection run timed out at 240 seconds.
  Every runner fingerprint reported the tree unchanged, but no completed
  positive review exists. The failed runs surfaced two real defects:
  caller-owned lists remained mutable after frozen-contract construction, and
  a caller could forge aggregate totals in an otherwise monotonic shadow.
  Both are fixed and covered by negative regressions; this does not convert the
  failed review attempts into an independent pass.

## Manual Checks

- [x] Confirm no raw prompt, repository content, credentials, provider bodies,
  or account identifiers are persisted.
- [x] Confirm every integrity report states the unkeyed/user-writable and
  suffix-truncation limitations.
- [x] Confirm learned evidence has no permission, gate, convergence, verifier,
  or Owner-authority field.
- [x] Confirm the store disclaims evidence existence, pass-status, and
  independent-process proof; those remain live-controller obligations.
- [ ] Independent Codex verification against a frozen tree.
- [ ] Claude peer review when usage returns.

## Documentation Updates

- [x] Delta spec updated.
- [x] Build Blueprint updated.
- [x] Backend change plan and ownership map recorded.
- [x] User-facing docs deferred because this packet does not wire a live
  operator workflow.
- [ ] Living spec sync deferred until archive.

## Backend Evidence

- Classification: local data mutation and agent-orchestration substrate.
- Function inventory: immutable contract constructors/parsers; one run-ledger
  append/read/verify boundary; pure profile shadow reducer; one optimistic
  profile commit/read/verify boundary.
- Inputs and validation: exact schemas, duplicate-key and non-finite refusal,
  identifier/reference/timestamp/digest validation, byte/depth/count/integer
  bounds, secret-shaped value checks, and forbidden raw-content field names.
- Auth/authorization: no network route, account, credential, tenant, or remote
  authorization surface is added. Learned data grants no effect authority.
- Mutation safety: OS plus in-process locking, existing-chain verification
  before append, contiguous allocation under lock, append+flush+fsync,
  duplicate observation refusal, optimistic state digest, and monotonic
  transition validation.
- Verification boundary: the profile store requires the controller's exact
  `verified` assertion and safe relative evidence reference, but does not claim
  to authenticate or inspect that evidence. Live integration is responsible
  for binding an accepted separate-verifier result.
- Secrets/logging: persistent schemas store digests, bounded metadata, safe
  references, raw aggregate counts, and error summaries only. Arbitrary
  secret detection is not claimed.
- Integration behavior: no provider call, credential access, retry loop,
  scheduler, permission change, or live adapter integration in this packet.
- Performance/cost: no model/API cost; run ledgers are capped at 16 MiB/10,000
  records and profile history at 128 MiB/10,000 commits, with 256 profiles and
  512 observations per commit.
- Silent behavior: none; new modules are additive and no current caller imports
  them.
- Kill switch / rollback: live behavior has no switch because it is not wired.
  Rollback is removal of the additive modules and packet before integration.
- Negative proof includes traversal-shaped IDs, secret/raw fields, oversized
  values, partial usage, corrupt/reordered streams, incomplete lines,
  concurrent writers, mutable caller lists, replay, stale-state conflict,
  exact-source aggregate forgery, and unverified terminal status.

## Result

IMPLEMENTATION CHECKS PASS; INDEPENDENT REVIEW PENDING. The local substrate is
not live routing, is not archive-ready, and is not release authorization.
Claude remains required to review the contracts, integrity claims, learning
attack surface, and future calibration before integration.
