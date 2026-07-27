# Claude Readiness Re-review Result

## Scope

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

## Blocking Concern

The readiness record was keyed by `CODEX_THREAD_ID` and validated the task ID,
runtime digest, and repository root, but carried no freshness or per-invocation
binding. A record from an earlier resume of the same thread could therefore
survive hook disablement and still return `current_revision_observed`.

Repository inspection reproduced the mechanism: the live record has no time,
nonce, or activity field, and the positive readiness regression hand-writes a
matching record without executing a hook. The peer gate remains open.

## Material Gaps And Risks

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

## Required Next Gate

Add a bounded same-invocation activity marker or weaken the execution claim,
then rerun the exact scoped cross-family review. Do not start the integrated
end-to-end dogfood or authorize release/archive from this result.
