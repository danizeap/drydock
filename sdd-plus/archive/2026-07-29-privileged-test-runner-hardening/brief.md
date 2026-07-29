# Brief

## Change

privileged-test-runner-hardening

## User Need

The Owner needs mutating delegation to run explicit project tests without
turning an apparently bounded test option into an unreviewed shell running
with the controller user's full permissions.

## Problem

`scripts/conductor/mutate.py --test-cmd` passes caller-supplied text to
`subprocess.run(..., shell=True)`. The command-shape checker only decides
whether a result may clear the merge gate; it does not constrain the command's
effects. A model-controlled shell string can therefore execute outside the
Codex worker sandbox, and Windows executable search can select a program
planted in the worktree. LaunchGuardian correctly blocks release on this
reachable privileged surface.

## Scope

In scope:

- Compile and validate the test plan before worktree creation or Codex spawn.
- Add an explicit structured-argv CLI/API contract.
- Retain a bounded compatibility adapter for simple legacy `--test-cmd`
  strings and `&&` chains, but reject shell operators instead of executing
  them.
- Resolve each executable to an absolute trusted PATH entry before delegation.
- Prepare and pin a model-free `codex sandbox` runner before delegation.
- Run steps through that runner with `shell=False`, sequential
  short-circuiting, one total timeout budget, worktree-only writes, and direct
  network disabled.
- Attempt bounded process-tree termination when a sandbox readiness probe or
  test times out and report whether that cleanup was confirmed.
- Add negative tests proving rejected plans do not spawn a worker or test
  process.
- Update the living contract, operator documentation, and LaunchGuardian
  evidence.

Out of scope:

- Claiming filesystem read isolation on native Windows. The local spike proved
  write and direct-network denial but also proved that an explicit deny profile
  could still read the Owner checkout on this installed alpha build.
- Automatically installing dependencies.
- Redesigning or deleting the legacy mutation/worktree implementation.
- Changing the new Codex-host `process_runner.py`.
- Fixing LaunchGuardian CLI's Windows decoding or Semgrep disposition model.
- Committing, publishing, or waiving release findings.

## Acceptance Criteria

- [x] No `shell=True` test execution remains in the legacy mutation runner.
- [x] Unsafe legacy strings fail before Codex discovery/spawn and never run.
- [x] Structured argv and safe legacy commands still produce honest
  green/red test evidence.
- [x] `&&` compatibility short-circuits without invoking a shell.
- [x] Worktree-planted executables cannot win executable search.
- [x] Windows batch/command shims are refused rather than implicitly executed
  through a shell.
- [x] Direct known shell launchers are refused, while transitive shell
  invocation by an allowed executable is disclosed rather than claimed
  prevented.
- [x] Tests fail closed when the Codex sandbox runner cannot be prepared.
- [x] Sandboxed tests cannot write outside the assigned worktree or open a
  direct network socket on the supported local Windows runtime.
- [x] Results and documentation disclose that native-Windows host read
  isolation is not established.
- [x] Timeout results expose process-tree cleanup evidence and ordinary results
  label write/network restrictions as requested configuration rather than
  per-run verified facts.
- [x] Focused, full legacy, Codex-adapter, parity, packet, and LaunchGuardian
  checks are recorded without calling skips or scanner absence a pass.

## Impact Areas

- Backend: privileged subprocess test runner and CLI parsing
- Frontend:
- Data model:
- API: `mutate(..., test_cmd=...)`, `run_tests`, and CLI test-plan options
- AI/model behavior: unsafe model-supplied test strings block before delegation
- Documentation: operator guide, capability delta, release evidence
- Operations/security: removes an implicit shell, confines persistent writes,
  disables direct network, and keeps the residual host-read boundary explicit

## Open Questions

- Whether a future Windows Codex release, WSL runner, or container runner can
  enforce filesystem read isolation strongly enough to remove the native
  Windows disclosure.
