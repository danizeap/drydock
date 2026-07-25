# Independent Peer Review Request

Status: Round 2 completed with `converged: true` and no blocking concerns.
The exact returned JSON is preserved in `peer-review-round-2.json`.

Review the active `privileged-test-runner-hardening` packet as an adversarial
security and architecture peer. Do not trust its verification report as proof;
inspect the implementation and tests directly.

Read:

- `sdd-plus/changes/privileged-test-runner-hardening/brief.md`
- `sdd-plus/changes/privileged-test-runner-hardening/plan.md`
- `sdd-plus/changes/privileged-test-runner-hardening/decision-log.md`
- `sdd-plus/changes/privileged-test-runner-hardening/specs/codex-conductor.md`
- `sdd-plus/changes/privileged-test-runner-hardening/verification.md`
- `scripts/conductor/mutate.py`
- `tests/test_mutate.py`
- `tests/fake_codex.py`
- the test-plan section of `docs/AI_OPERATOR_GUIDE.md`

Answer these questions from code:

1. Can any invalid, forged, or shell-shaped test plan reach Codex discovery,
   worktree creation, the mutating worker, or a direct controller process?
2. Can the worker replace the pinned test executable through the worktree,
   `PATH`, temporary storage, a Windows batch shim, or a TOCTOU?
3. Does every approved step run through the intended model-free Codex sandbox
   with no direct fallback, one total timeout, short-circuiting, filtered
   environment, direct network denial, and worktree-only writes?
4. Can Owner or worker project config weaken the explicit CLI permission
   profile or Windows backend? Distinguish what code proves from the
   point-in-time live probe.
5. Are dynamic TOML/config arguments encoded safely on Windows paths containing
   spaces, quotes, or backslashes?
6. Are background or descendant processes, timeout cleanup, test-created
   artifacts, and post-test worktree state handled honestly?
7. Does the result overclaim read isolation, scanner coverage, or test
   verification?
8. Is any blocker missing from the delta spec or hostile regression matrix?

Return JSON:

```json
{
  "converged": false,
  "overall": "one concise paragraph",
  "blocking_concerns": [],
  "gaps": [],
  "risks": [],
  "required_changes": []
}
```

Set `converged` to `true` only when no blocking concern remains. Absence of a
finding is not proof that a platform boundary exists.

## Round 2 focus

The first independent review returned `converged: false` with one blocker and
two required implementation gaps:

- the broad shell-launcher SHALL was bypassable through `env`, interpreters,
  and other transitive launchers;
- timeout handling did not reap or disclose descendant processes;
- result metadata labelled requested write/network configuration as achieved
  facts.

The current working tree claims to remediate those items. Recheck the code and
tests rather than trusting this summary. In particular:

1. Confirm the spec, operator guide, CLI help, code, and tests now limit refusal
   to directly selected known shells and Windows batch shims, while explicitly
   denying any claim that an allowed executable cannot invoke a shell
   transitively.
2. Confirm known indirection/interpreter shapes produce an advisory and that
   the advisory cannot be mistaken for prevention.
3. Inspect `_start_test_process`, `_terminate_test_process_tree`, and
   `_run_test_step` for Windows/POSIX timeout races, unsafe process targeting,
   unbounded waits, output-pipe hangs, or a path that leaves the direct sandbox
   process alive without disclosing it.
4. Confirm timeout results expose cleanup evidence and the escaped-descendant
   limitation. Treat the fake-sandbox descendant regression as process-lifetime
   evidence only, not proof of Codex filesystem containment.
5. Confirm sandbox metadata uses requested/per-run-unverified labels and does
   not retain achieved-sounding aliases.
6. Confirm post-test artifacts and active Codex-home/managed configuration are
   disclosed as residual trust/state.
7. Look for any new blocker introduced by the remediation, not only closure of
   the prior findings.

Current implementing-agent evidence is `74 passed` focused,
`548 passed, 6 skipped` legacy, and `94 passed, 2 skipped` Codex adapter.
Those counts are claims to verify, not a substitute for review. LaunchGuardian
is independently still `BLOCKED` on 7 high and 2 medium findings.
