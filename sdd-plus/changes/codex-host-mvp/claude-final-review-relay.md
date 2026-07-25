# Claude Final Review Relay

Please review this as Drydock's existing architectural peer. This is the final
implementation convergence gate, not a request to restate the blueprint.

Your last blocker was that a Windows Job Object proves descendant lifetime
only, while an escaped worker could poison repository-local Git configuration
and make trusted post-worker Git execute `core.fsmonitor` or hooks.

The attached revision now:

- captures the exact Windows process identity while the child is suspended
  inside a kill-on-close Job Object and labels that evidence
  descendant-lifetime containment only;
- resolves Git once from absolute PATH entries before delegation and invokes
  only that absolute executable afterward, including the reserved-container
  ignore preflight;
- refuses local Git config include directives and external
  clean/smudge/process filters before worktree creation;
- directly fingerprints a bounded Git control surface after worktree creation
  and before launch: repository/worktree config, active HEAD/refs, indices,
  hooks, attributes/excludes, alternates/replacements, and worktree admin
  pointers;
- terminates the Job and compares that fingerprint before the first
  post-worker Git command;
- pins filesystem monitoring, hook path, external attributes/diff, symlink,
  and untracked-cache config on runner Git;
- checks Owner HEAD/tree fingerprint before diff extraction, reports no
  delegated evidence on drift, and rechecks control and Owner state after
  extraction;
- streams the no-follow worktree boundary scan with a 100,000-entry cap and
  refuses extraction or recursive cleanup as soon as that cap is exceeded;
- keeps every mutation result non-green until separate verification and
  deliberate integration.

Hostile regressions prove `.git` redirect/delete refusal, local fsmonitor/hooks
poisoning without sentinel execution, absolute Git invocation, include/filter
refusal before spawn, Owner drift before extraction, junction/hardlink refusal,
background-descendant shutdown, strict/duplicate-key JSON, and exact verifier
state binding.

Current evidence:

- Codex adapter: 94 passed, 2 symlink-privilege skips (not positive evidence).
- Legacy Claude host: 501 passed, 6 skips.
- Two real fixed-root Codex workers: exact in-root bytes, Owner fingerprint
  unchanged, Git-control fingerprint unchanged, no ignored files,
  `merged: false`, non-green `review_required`, exact cleanup. The latest ran
  after the absolute-preflight and streamed-scan corrections.
- Real separate read-only verifier: schema-valid PASS on the two requested
  checks with identical pre/post HEAD and tree fingerprint.
- Earlier live containment probe under a `danger-full-access` parent wrote the
  assigned worktree and was denied a sibling Owner-checkout write. This is the
  filesystem evidence; the Job Object is not used to make that claim.
- Strict LaunchGuardian framework scan is independently BLOCKED on 8 high
  findings. Code convergence must not be reported as release clearance.
- Three new direct Opus calls produced no critique: one hit its $1.25 ceiling
  and two successively smaller reviews timed out at 300 seconds. All still
  reported first-party authentication ready and requested model
  `claude-opus-5`; none reported Fable quota exhaustion or model
  unavailability. They are neither agreement nor rejection.

Audit the attached exact runner, hostile tests, normative spec, and blueprint.
Look specifically for a reachable executable/TOCTOU chain, cleanup blast-radius
error, Windows identity/lifetime overclaim, Git filter/config escape, or
parser fail-open.

Return only:

```json
{
  "converged": false,
  "overall": "one honest paragraph",
  "blocking_concerns": [],
  "gaps": [],
  "risks": [],
  "required_changes": []
}
```

Set `converged: true` only if `blocking_concerns` is empty. A blocker must name
the concrete reachable failure chain and the required correction. Put
LaunchGuardian remediation and cross-platform evidence portability in
gaps/risks unless they expose an implementation showstopper.

Attach these exact current files:

1. `adapters/codex/drydock/scripts/process_runner.py`
2. `adapters/codex/tests/test_process_runner.py`
3. `sdd-plus/changes/codex-host-mvp/specs/codex-host-orchestration.md`
4. `docs/CODEX_HOST_BUILD_BLUEPRINT.md`
