# Integrated dogfood negotiation evidence

## Status

- Plan: `integrated-dogfood-plan.md`.
- Requested peer: exact `claude-opus-5`.
- Configured round cap: 2.
- Initial cycle result: not converged at the cap.
- Fresh Owner-authorized cycle result: converged in Round 2 with no blocking
  concern.
- 2026-07-29 execution rebase: BLOCKED. Round 1 was non-converged; Round 2
  returned no critique because the configured provider budget was exhausted.
  The earlier convergence does not cover the current guide preimage or the
  hardened clean-candidate, full-suite-proof verifier flow.
- 2026-07-29 superseding cycle: active as new durable run
  `7156538ebf4a4f0ea4ae283a3bf734bb`. The prior blocked ledger is unchanged.
  This cycle permits at most two peer calls, `$1.50` configured provider
  ceiling per call, and `$3.00` total peer-phase ceiling.
- Mutation process started: no.
- Worktree created: no.
- Integration or push performed from this plan: no.

## 2026-07-29 execution rebase — Round 1

- Run ID: `73318eaf444b429d952e0fbe09119056`.
- Reviewed clean HEAD:
  `347d06a3eff7587a9a3d41259b7179527a21b8fe`.
- Reviewed v2 executable fingerprint:
  `c1ae2c92f0df895d57ebf40fbfdea31d04953758cfa43a16b5b939641405403e`.
- Controller result: schema-valid; `pre_mutation_critique.gate_satisfied:
  false`; no worker started.
- Requested `claude-opus-5` observed, with the CLI's Haiku helper also
  reported.
- Outbound input: 19,467 bytes.
- Elapsed peer phase: 257.34 seconds.
- Observed provider cost: `$0.702121` against the configured `$1.50` call
  ceiling.
- Verdict: `converged: false`, four blockers.

Reconciliation:

- Accepted: add an execution-time exact guide-blob/anchor/postimage freshness
  gate and pin the actual clean worktree base before launch.
- Refined from source: the runner already pins `core.hooksPath` to the null
  device, disables fsmonitor/external diff/textconv, scrubs inherited Git
  environment, nulls global/system config, and recursively fingerprints the
  bounded common hooks directory. The peer's statement that hooks are outside
  every fingerprint is false for the runner. The plan now repeats equivalent
  pins for the later control-plane commit/push and broadens direct config and
  remote checks instead of changing the reviewed runner.
- Accepted as claim correction: the prior failed Render MCP cleanup attempt is
  positive counterevidence to no-egress wording. The plan now claims only
  requested argv/profile configuration, retains the complete reported worker
  event stream, and treats absence of a host-reported connection attempt as
  unknown.
- Accepted: the Round-2 peer receives the complete frozen note and both
  adjacent paragraphs, not only the note digest.
- Accepted gaps: both anchor uniqueness checks; 50,224-byte post-fast-forward
  on-disk expectation; public-remote and prior-disclosure recheck; no-retry
  partial/unconfirmable-push behavior; enumerative ignored-injection wording;
  point-in-time hook interpreter identity; and verifier #2 as freshness
  binding rather than independent corroboration.

## 2026-07-29 execution rebase — Round 2 transport result

- Reviewed clean HEAD:
  `50960cc0f853daac824d42fa3fd058831b5c0466`.
- Reviewed v2 executable fingerprint:
  `d4efc96fb8d3ad2c90c1028faabd8404a5623464dfc08a37c70bd41f96bc6d96`.
- Configured call ceiling: `$0.50`, the only remaining amount inside the
  two-call `$2.00` phase envelope.
- Elapsed call time: 205.04 seconds.
- Outbound input: the cumulative phase total became 47,801 bytes.
- Provider result: exit 1, `error_max_budget_usd`.
- Controller classification: `structured_budget_ceiling`.
- Critique/schema verdict: absent. No blocker closure, convergence, model
  judgment, or content review is inferred.
- Observed cumulative phase provider cost: `$1.322007`; configured cumulative
  provider reservation: `$2.00`.
- Gate: `pre_mutation_critique.gate_satisfied: false`,
  `peer_convergence: not_established`, workflow action `return_to_owner`.
- Durable run `73318eaf444b429d952e0fbe09119056` was closed with status
  `blocked`.
- Mutation process started: no.
- Worktree created: no.
- Commit/integration/push from this dogfood plan: no.

## 2026-07-29 one-use Owner authorization

The Owner explicitly authorized:

1. One fresh durable peer cycle for this exact existing
   `codex-host-mvp` dogfood objective. It supersedes rather than restarts or
   reinterprets closed blocked run `73318eaf444b429d952e0fbe09119056`.
   Each peer call has a `$1.50` provider-reported ceiling and the two-call peer
   phase has a `$3.00` total ceiling.
2. One non-force push to
   `origin/codex/codex-host-mvp-checkpoint` only if plan convergence, isolated
   mutation, cross-review, exact candidate proof, separate verification,
   integration, clean-tree, remote/preimage, and every packet gate all pass.

The authorization does not permit force push, another destination, merge to
another branch, archive, release, publication, deployment, weakened
verification, a third peer round, or continuation after an unknown, failed,
stale, malformed, mismatched, unavailable, or unproven gate. It is consumed
once by this exact cycle.

The first new-run command attempted to pass closed run
`73318eaf444b429d952e0fbe09119056` as `--previous-run-id`. The controller
returned `{ok:false, stage:"input_error", error:"only an active run may be
superseded"}` and created no run. The closed ledger remains unchanged. The
fresh cycle therefore uses an independent new run ID, while this packet records
the predecessor relationship; it does not restart, reopen, supersede in-place,
or reinterpret the blocked run.

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

## Fresh negotiation cycle

The Owner explicitly directed Codex to continue, authorizing a new bounded
two-round cycle rather than silently exceeding the first cap.

### Fresh Round 1

- Controller result: schema-valid.
- Requested `claude-opus-5` observed: yes.
- Cost: `$0.989484` against a `$1.00` ceiling.
- Verdict: `converged: false`, one blocker.
- The peer withdrew both first-cycle blockers after reviewing the direct Git
  controls and locale discriminator.
- The remaining concern was verifier-target ambiguity: if the first verifier
  were pointed at the Owner checkout, the reserved ignored worktree could make
  a PASS vacuous.
- The peer required an exact `--repo <mutation-worktree>` invocation and a
  linked-worktree fingerprint-sensitivity proof.

Codex then created a bounded linked worktree at
`C:\Users\Daniel Paez\drydock\.drydock-worktrees\772ec131d9b7`.
`canonical_repo()` returned that exact root. Its fingerprint changed from
`db0120d86d0540fd9a054b7a3409fd524a8e75a88a1078ed74d24453e81cf852`
to
`7e94ffbc6a6b2f5468dfcaa0df6875e2f7c940c806a2871a46bfb6c5e1fff82e`
when one scratch file appeared, then returned exactly to the first digest after
removal. Bounded cleanup removed the worktree, branch, and lease without a
boundary error.

### Fresh Round 2

The first capture attempt was a transport failure: the local shell wrapper
detached while the bounded controller and Claude child remained alive. Codex
started no duplicate while they ran, confirmed both processes exited, and
received no recoverable structured stdout. That attempt supplies no verdict,
model-usage proof, or convergence evidence.

One controlled capture retry then returned:

- Controller result: schema-valid and `ok: true`.
- Requested `claude-opus-5` observed: yes.
- Peer status: `operational_ready`.
- Cost: `$0.4510125` against a `$1.00` ceiling:
  `$0.4472615` Opus 5 and `$0.003751` observed Haiku routing.
- Verdict: `converged: true`.
- Blocking concerns: none.
- Controller loop: `continue: false`, reason `converged at the round cap`.

The peer accepted the plan's scope, locale mechanism, narrow claims,
Git-control safeguards, linked-worktree sensitivity, and verifier
anti-replay/epistemic-independence distinction. It returned precision gaps
rather than blockers:

1. pre-register exact blank-line splice bytes and post-mutation raw/blob
   hashes;
2. prove the guide is not a sync mirror;
3. specify the second verifier as precisely as the first;
4. name the out-of-band Owner push authorization rather than letting plan text
   authorize itself;
5. pin the control-plane Python interpreter and suppress bytecode caches;
6. reference the already tracked runtime locale remediation.

Codex implemented those deterministic refinements before freezing the plan.
The peer did not inspect the resulting wording as a third round, and no third
round is inferred. The changes add commitments and preconditions without
expanding the mutation or its authority; the exact diff remains subject to
cross-review and separate verification.

## Current gate consequence

The fresh cycle supplies schema-valid Opus 5 convergence with no blocker.
Planning agreement is therefore satisfied for the frozen one-file mutation.
This does not authorize release, archive, merge, publication, deployment, or
personal plugin changes, and it does not make either model an independent
verifier. Mutation remains gated on the pre-mutation deterministic checks and
on committing the frozen plan/note evidence into the runner's base.

## Post-worker mechanism correction

After the one-file worker completed, Codex attempted the plan's stated
pre-verifier `_assert_safe_local_git_configuration()` call. It did not pass:
Git refuses `config --worktree` after a linked worktree exists unless
`extensions.worktreeConfig` is enabled. No verifier, integration, or additional
worker was started from that failed check.

The runner had already executed the same safe-config precheck before worktree
creation, and its `GitControlBoundary` fingerprint was unchanged across worker
execution and extraction. Codex directly parsed the existing config files named
by that boundary with `git config --file <exact-path> --no-includes
--name-only --list`; no include or external filter key was present. The plan
was amended to use that actual carry-forward mechanism rather than report an
unusable helper call as passing.

The worker stderr also contained a failed `DELETE` cleanup attempt for a Render
MCP session despite the requested empty-MCP/disabled-feature contract. The
channel was closed, so the output does not establish a remote state change. It
does establish that zero MCP transport was not proven. The amended plan records
that residual and retains the exact mutation for cross-review; this correction
does not widen worker scope or outward authority.
