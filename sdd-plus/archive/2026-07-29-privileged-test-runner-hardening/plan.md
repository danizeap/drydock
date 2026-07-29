# Plan

## Change

privileged-test-runner-hardening

## Approach

1. Freeze a `TestPlan` contract that accepts either structured argv or a
   compatibility string containing only simple commands and `&&`.
2. Parse and validate the complete plan before Codex discovery, gauge reads,
   worktree creation, or delegation.
3. Resolve bare executable names from absolute parent PATH entries before the
   worker can write; refuse worker-writable temporary roots, relative/absolute
   caller paths, direct known shell launchers, Windows batch/command shims,
   empty arguments, NUL/newline content, and bounded-plan overflows. Treat
   transitive shell invocation by an allowed executable as unprevented and
   advisory rather than extending a launcher denylist into a false boundary.
4. Prepare and pin the installed Codex CLI's model-free `sandbox` command
   before the mutating worker starts. Refuse mutation when that boundary is
   unavailable.
5. Execute absolute argv steps through an explicit worktree-write,
   network-disabled sandbox profile with `shell=False`, one total deadline,
   captured output, and short-circuit-on-failure semantics.
6. Preserve honest gate behavior: invalid plans are structured pre-spawn
   failures; test failures are red; timeouts are non-green; runner delegation
   remains advisory.
7. On readiness or test timeout, attempt bounded process-tree termination with
   a POSIX process group or Windows `taskkill /T`, surface
   confirmation/limitations, and disclose that escaped descendants are not
   prevented.
8. Label write scope and direct-network denial as requested sandbox
   configuration unless verified for that individual run. Disclose that tests
   execute after diff extraction and may leave unstaged artifacts.
9. Update tests, delta spec, operator docs, packet evidence, and rerun
   LaunchGuardian in strict framework mode.

## Backend Change Plan

Classification: privileged local process execution / security hardening

Existing pattern found: stdlib-only subprocess helpers, structured result
dictionaries, bounded timeouts, fail-closed merge-gate trust, pytest
monkeypatches, and real temporary worktrees.

Design choice: compile the test plan before the mutating worker starts and pass
only an immutable absolute-argv plan into post-worker execution. Keep the
logic inside `scripts/conductor/mutate.py` because it owns the legacy test
gate; do not introduce a dependency or generic command framework.

Risks before coding:

- Shell-string compatibility can break for operators that were previously
  executed but merely labelled untrusted.
- Cross-platform quoting differs; JSON argv is the unambiguous escape hatch.
- Windows `.cmd`/`.bat` files can invoke the command processor even with
  `shell=False` and must be refused.
- The native Windows sandbox on this machine enforces write and direct-network
  boundaries but did not enforce explicit read denies. The implementation must
  disclose that residual host-read surface and never call it full filesystem
  isolation.
- A timed-out sandbox process can leave descendants alive and lock the
  worktree. Cleanup must be attempted and evidenced without claiming that a
  process escaping the OS grouping mechanism was reaped.

Stop conditions:

- A code path still invokes caller-controlled test text through a shell.
- The executable can be resolved from the worker-writable worktree.
- Invalid test input reaches Codex or creates a worktree.
- Tests require a new runtime dependency or a platform-specific shell.
- Test execution falls back to the controller process when Codex sandbox
  preparation or launch fails.

## Files Expected To Change

- `scripts/conductor/mutate.py`
- `tests/test_mutate.py`
- `tests/test_mutate_ergonomics.py` only if its call contract changes
- `docs/AI_OPERATOR_GUIDE.md`
- `sdd-plus/changes/privileged-test-runner-hardening/*`
- `sdd-plus/changes/privileged-test-runner-hardening/specs/codex-conductor.md`
- generated LaunchGuardian reports

## Risks

- Existing users relying on pipes, redirects, shell built-ins, or batch shims
  will receive a structured refusal and migration guidance.
- Static scanner clearance can expose a different finding; the release remains
  blocked until a fresh complete report says otherwise.
- Codex permission profiles are beta and this installed CLI is alpha-versioned;
  readiness and regression evidence are point-in-time, not a permanent
  platform guarantee.

## Rollback

Omit the test plan to disable test execution. A code rollback can restore the
previous API, but restoring `shell=True` reopens the security finding and is
not an acceptable release resolution.
