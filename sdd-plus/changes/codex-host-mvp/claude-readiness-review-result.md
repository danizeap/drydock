# Claude Readiness Re-review Result

## Round 1 Scope

- Baseline: `07d2be3` (prior converged Opus review recorded)
- Reviewed delta: `07d2be3..40adbf5`
- Requested model: `claude-opus-5`
- Transport: first-party Claude Max, exact requested model observed, structured
  output only
- Result: `converged: false`
- Cost evidence: `$0.6880055` against a `$1.25` ceiling

The first output wrapper lost its pipe after a five-second launcher timeout.
That process was allowed to finish and was not treated as a verdict. One clean
retry completed in 201.3 seconds and produced the result summarized here.

## Round 1 Blocking Concern

The readiness record was keyed by `CODEX_THREAD_ID` and validated the task ID,
runtime digest, and repository root, but carried no freshness or per-invocation
binding. A record from an earlier resume of the same thread could therefore
survive hook disablement and still return `current_revision_observed`.

Repository inspection reproduced the mechanism: the live record has no time,
nonce, or activity field, and the positive readiness regression hand-writes a
matching record without executing a hook. The peer gate remains open.

## Round 1 Material Gaps And Risks

- The spec and operator wording attributed the record to a trusted
  SessionStart hook although the unsigned file itself cannot prove that
  provenance.
- Discovery requires exactly one candidate path, not exactly one
  content-matching record.
- The intermediate `liveness/` directory was not checked for symlink or
  Windows reparse-point redirection.
- The two denial probes need a benign allow control before they can show
  selective policy behavior rather than only denials.
- Resolution labels need small consistency fixes, including an empty
  `CODEX_THREAD_ID`.
- Plugin-data evidence remains agent-writable and forgeable. This is compatible
  only with the explicitly cooperative, non-managed guardrail profile and must
  remain disclosed.

## Round 1 Required Next Gate

Add a bounded same-invocation activity marker or weaken the execution claim,
then rerun the exact scoped cross-family review. Do not start the integrated
end-to-end dogfood or authorize release/archive from this result.

## Round 2 Result

- Reviewed delta: `40adbf5..79cb83f`
- Requested model: `claude-opus-5`
- Result: `converged: true`
- Blocking concerns: none
- Runtime: 218.5 seconds
- Cost evidence: `$0.8256345` against a `$1.25` ceiling

Opus found that the explicit readiness CLI probe, separate recent PreToolUse
activity record, 10-second age bound, 2-second future-skew bound, linked-path
rejection, and unsigned/in-window replay disclosures close the resume-replay
blocker for the cooperative, non-managed, user-disableable profile. It
explicitly did not authorize release, archive, merge, or publication.

The supported claim is narrow: a digest-bound guarded Bash PreToolUse runtime
was recently live for the thread and repository. It is not hostile-agent
attestation, host-reported trust/enablement, or universal tool coverage.

## Round 2 Follow-up Gaps

Before producing the final install candidate, Codex accepted and corrected the
cheap precision gaps:

- current `model` and `permission_mode` now come from the fresh PreToolUse
  activity record rather than the unbounded SessionStart record;
- probe recognition tokenizes the command and requires a
  `drydock_codex.py`, `readiness` token sequence plus the exact probe flag;
- the recorded hook event now comes from the validated payload;
- regressions cover quoted false probes, apply_patch non-marking, a junctioned
  `activity/` directory, exact time boundaries, and the decoded digest chain.

The peer's latency concern did not reproduce in code: readiness evaluates
enforcement evidence before the optional Claude authentication status check.
Live dogfood must still measure the actual marker age and must not widen the
window merely to force a positive result.

This round authorizes the next current-revision install/live dogfood gate only.
The packet's final independent review remains pending until it can inspect the
live evidence for the exact installed digest.
