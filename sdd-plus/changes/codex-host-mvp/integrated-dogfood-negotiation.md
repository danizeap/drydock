# Integrated dogfood negotiation evidence

## Status

- Plan: `integrated-dogfood-plan.md`.
- Requested peer: exact `claude-opus-5`.
- Configured round cap: 2.
- Result: not converged at the cap.
- Mutation process started: no.
- Worktree created: no.
- Integration or push performed from this plan: no.

## Round 1

- Controller result: schema-valid.
- Requested model observed: yes.
- Cost: `$0.2588095` against a `$1.00` ceiling.
- Verdict: `converged: false`, three blockers.
- Accepted corrections:
  - add the concrete source/reproduction evidence bundle;
  - narrow the false-green statement and freeze exact wording;
  - name `origin/codex/codex-host-mvp-checkpoint` as the only push target;
  - add baseline gates, runtime-digest checks, detective one-file scope,
    post-integration verification, and explicit residual boundaries.

## Round 2

- Controller result: schema-valid.
- Requested model observed: yes.
- Cost: `$0.4821165` against a `$1.00` ceiling.
- Verdict: `converged: false`, two blockers.
- The controller returned `continue: false` because the round cap was reached.

The two final concerns were:

1. The peer asserted that the worker could rewrite the linked worktree `.git`
   pointer, evade changed-file extraction, and redirect later Git evidence.
2. The peer required the identical verifier to be rerun with
   `-X utf8=1` before accepting locale decoding as the cause of the generic
   integrity denial.

## Post-cap Codex audit

### Git-control concern

The factual premise does not match the current runner:

- `process_runner.py` captures the worktree `.git` pointer bytes and SHA-256 in
  `WorktreeBoundary`.
- `_assert_worktree_boundary` verifies the exact pointer before each
  `_run_worktree_git` call.
- Post-worker Git uses explicit `--git-dir` and `--work-tree`, pinned
  configuration, controlled environment, and an absolute Git executable.
- `git_control_fingerprint` covers the trusted common, Owner, and worker Git
  control surfaces before worker launch, after process-tree shutdown, and
  after extraction. Drift refuses all later evidence.
- `_extract_changes` stages into a temporary index/object directory with
  `git add -A`, so tracked and untracked changes enter the bounded diff.
  `git status --porcelain=v1 --ignored=matching --untracked-files=all`
  separately reports ignored artifacts, which block the handoff.
- `test_worker_git_link_tamper_cannot_redirect_runner_git` covers pointer
  replacement and deletion and asserts refusal before redirected Git can
  mutate the Owner index or object database.

This is narrower and stronger than the peer's proposed broad recursive
inventory for the concrete redirect chain. It does not claim a universal
filesystem inventory.

### UTF-8 discriminator

Codex executed the installed handler's exact apply_patch verifier command in
two modes: current `py -3 -I -S` and the same command with
`-X utf8=1`. The plugin root, payload bytes, runtime, and policy were otherwise
identical.

| Case | UTF-8 bytes | Current locale mode | Forced UTF-8 mode |
|---|---|---|---|
| ASCII | `70 6c 61 69 6e` | allowed | allowed |
| em dash | `e2 80 94` | allowed | allowed |
| U+0081 | `c2 81` | generic integrity deny | allowed |
| U+008D | `c2 8d` | generic integrity deny | allowed |

Each pair used the same payload SHA-256 in both modes. The installed
`runtime.py` SHA-256 before and after was
`a04cf380e435e4a39640d10886fcf82d0176233ee6b974854bb03cc158c9bc4b`.
Together with `build_hooks.py` reading text through `sys.stdin.read()` before
`original.encode('utf-8')`, this distinguishes host-locale decode failure from
runtime-integrity failure for the undefined-byte cases. It does not prove that
all non-ASCII policy decisions are unaffected.

## Gate consequence

Both final concerns now have concrete Codex evidence, but the peer has not
reviewed that evidence. The configured two-round agreement cap is exhausted.
Drydock therefore does not infer convergence and does not start the mutating
worker. A new negotiation cycle or Owner-directed manual peer relay is required
before the integrated dogfood can continue.
