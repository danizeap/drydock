# Verification

## Change

privileged-test-runner-hardening

## Automated Checks

- [x] Focused mutation/test-plan regressions on the peer-remediated code:
  `74 passed` in 15.25s.
- [x] Complete legacy/Claude-host suite refreshed after the release-gate
  edits: `548 passed, 6 skipped` in 77.63s.
  The skips are recorded as skips, not positive evidence.
- [x] Complete Codex-adapter suite refreshed after the release-gate edits:
  `94 passed, 2 skipped` in 94.03s.
  Both skips require Windows symbolic-link privilege and are not counted as
  positive evidence.
- [x] The two current complete suites total `642 passed, 8 skipped`. This is a
  sum of two independently completed commands, not a separately claimed
  combined-discovery run.
- [x] Root/scaffold parity: all 11 pairs identical.
- [x] Generated project-scaffold bundle and hook runtime/definition match their
  sources.
- [x] All five version declarations agree at `0.12.1` with a changelog entry.
- [x] `git diff --check` exited zero.
- [x] `python scripts/sdd.py verify privileged-test-runner-hardening`
  verified packet artifacts after the second peer verdict and reported
  `14 complete, 0 pending`. It mechanically reported the packet ready to
  archive; no archive was attempted because LaunchGuardian's separate release
  gate remains blocked.
- [x] Strict LaunchGuardian framework scan on the peer-remediated code was
  refreshed at `2026-07-25T14:03:54.497175Z` in forced UTF-8 mode with LGF
  validation valid and all five scanner adapters reporting `ran`.
  LaunchGuardian remains **BLOCKED** on 6 high and 0 medium findings. The prior
  `shell=True` finding remains absent. A separately approved Codex-host
  release-gate slice removed the mutable-action findings through verified
  full-SHA pins and removed the non-executable WebSocket prose false positive
  without changing its historical meaning. All six remaining findings are
  Python-3.6 compatibility rules outside the declared Python-3.9+ floor. No
  finding was waived or downgraded. Raw Semgrep output contains 20
  fixpoint-timeout warnings across other files, so adapter execution is not
  described as proof that every rule completed. The final normalized findings
  contain no finding for `mutate.py`; that absence is not promoted into
  scanner-completion proof.

## Manual Checks

- [x] Unsafe pipes, redirects, sequencing, backgrounding, `||`, newlines,
  command substitution, malformed quoting, directly selected known shell
  launchers, batch shims, overflow, forged plans, and invalid JSON are refused.
  A regression replaces Codex discovery/worktree/worker functions with
  sentinels and proves invalid input reaches none of them.
- [x] Twelve hostile indirection/interpreter shapes, including
  `env sh -c`, `xargs`, `timeout`, Python, and Node, compile as ordinary
  top-level argv but produce the explicit advisory that internal execution is
  unproven. This closes the broad no-shell overclaim without pretending a
  denylist can prevent transitive shell invocation.
- [x] Compiled executables are absolute regular files resolved before
  delegation. A worktree-planted same-name executable does not win; a PATH
  executable beneath worker-writable temporary storage is refused.
- [x] A real readiness probe succeeded with
  `codex-cli 0.146.0-alpha.3.1`.
- [x] Live native-Windows test runner probe:
  - an assigned-root write passed;
  - a direct out-of-root write failed with `PermissionError`;
  - the same write through a child Python process failed;
  - a direct socket to `1.1.1.1:80` failed with WinError 10013;
  - `DRYDOCK_TEST_SECRET` and `DRYDOCK_TEST_TOKEN` were absent in the child;
  - reading the Owner checkout succeeded, proving read isolation is not
    established and validating the disclosure rather than a stronger claim.
- [x] A hostile worktree `.codex/config.toml` requested both legacy
  `sandbox_mode = "danger-full-access"` and
  `default_permissions = ":danger-full-access"`. The exact runner still
  denied an out-of-root write. The command now also pins
  `windows.sandbox = "elevated"` and includes managed constraints.
- [x] A clean isolated `CODEX_HOME` was tested and could not reuse the
  installed elevated Windows sandbox; it failed readiness, and a bounded retry
  was terminated after timeout. The implementation therefore does not claim
  isolated-home support. It keeps the active Codex home as a disclosed,
  point-in-time TCB while pinning the relevant runtime reductions on the CLI.
- [x] Exact probe files and the isolated-home probe tree were bounded, checked
  for reparse points, removed after PowerShell deletion was policy-blocked, and
  confirmed absent. The denied outside targets never existed.
- [x] `rg` found no `shell=True` in `scripts/conductor/mutate.py`.
- [x] A real Windows timeout regression spawned a delayed descendant through
  the fake model-free sandbox, proved the descendant reached its post-spawn
  marker, timed out the outer runner, and observed that the descendant never
  wrote its delayed survival sentinel. The result reports `taskkill /T /F`,
  direct-process status, confirmation state, and that deliberately escaped
  descendants are not ruled out. The fake sandbox proves controller process
  grouping/cleanup behavior, not Codex filesystem enforcement.
- [x] A readiness-timeout unit regression proves the pre-worker probe uses the
  same grouped runner and turns an unconfirmed cleanup into an explicit
  `TestPlanError` rather than silently proceeding.
- [x] Results now report `requested_write_scope`,
  `requested_direct_network`, and
  `per_run_boundary_verification: not performed`; achieved-sounding
  `write_scope` and `direct_network` fields are absent.
- [x] Results warn that tests run after diff extraction and may leave unstaged
  artifacts in the retained worktree.
- [x] Independent peer verification. Claude's first review was non-converged
  with one valid blocker plus timeout-descendant and achieved-sounding metadata
  gaps. Its second review inspected the remediated code, independently
  reproduced `642 passed, 8 skipped`, returned `converged: true`, and reported
  no blocking concerns. The exact verdict is preserved in
  `peer-review-round-2.json`. Earlier timed-out Codex/Terra attempts remain
  unavailable evidence, not additional reviewers.

## Peer Review Reconciliation

- Accepted: the direct-shell claim, timeout lifecycle, and metadata corrections
  are closed by code and tests.
- Retained as non-blocking release-track work: explicitly name the Windows
  `taskkill /T` breakaway/re-parenting weakness and stronger Job Object option;
  separate high-signal indirection advisories from ordinary interpreter
  advisories; disclose the bounded cleanup/drain margin beyond `timeout_s`;
  keep the native-Windows host-read exposure visible.
- Refined: the current POSIX implementation already checks process-group
  liveness immediately before `SIGKILL`. Skipping group cleanup merely because
  the leader was reaped could leave descendants alive, so that proposed change
  was not applied. The remaining check-to-signal race is theoretical and
  non-blocking.
- Corrected against current generated evidence: the latest raw Semgrep output
  has fixpoint-timeout warnings, but none over `mutate.py`. The review's more
  specific statement is stale or scan-variable; rule completion still is not
  claimed.

## Documentation Updates

- [x] Operator guide updated with structured argv, sandbox readiness, write and
  network boundary, environment filtering, and native-Windows read limitation.
- [x] Project context did not require another change for this bounded hardening
  packet.
- [x] Delta spec updated before the sandbox implementation.
- [x] LaunchGuardian report and Codex-host finding triage updated.

## Result

**IMPLEMENTATION AND INDEPENDENT PEER PASS — RELEASE GATE BLOCKED.**

The privileged implicit-shell path is removed, direct known shell selection is
refused, and transitive execution is now disclosed rather than claimed
prevented. Approved tests fail closed into a pinned model-free Codex sandbox;
timeout cleanup is attempted and evidenced; ordinary results label
write/network settings as requested configuration. The supported Windows
machine retains point-in-time proof of outside-write and direct-socket denial
while disproving read isolation. Deterministic tests and parity checks pass,
and the second independent review converged with no blockers. LaunchGuardian
remains BLOCKED on six high findings, so this packet is not archived and the
Codex host is not release-ready.
