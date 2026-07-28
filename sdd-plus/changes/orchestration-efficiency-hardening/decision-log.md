# Decision Log

## Change

orchestration-efficiency-hardening

## Decisions

| Date | Decision | Reason | Alternatives Considered |
| --- | --- | --- | --- |
| 2026-07-28 | Efficiency work may remove duplicate work but not peer critique, independent verification, fail-closed gates, or final evidence | The Owner explicitly wants Drydock faster without making it less safe | Reduce proof or allow implementers to self-certify |
| 2026-07-28 | Treat the adaptive-ledger run as dogfood evidence, not a universal calibration dataset | One FULL run exposes mechanisms and failure modes but cannot justify precise global thresholds | Invent exact token savings and universal time limits |
| 2026-07-28 | Separate the first implementable hardening slice from a future repository-aware peer transport | Budget classification, single-flight, durable result capture, input preflight, and proof invalidation are bounded; safe repository read access needs its own threat model | Give the existing peer unrestricted Read tools immediately |
| 2026-07-28 | Key reusable proof to candidate, exact command, and relevant environment; unknown relationships invalidate | Reuse is safe only when the evidence still describes the same executable state and environment | Cache by branch name or latest successful result |
| 2026-07-28 | Peer budget violations return to the Owner | The active peer-unavailable delta already requires this, and live Opus/Fable calls exposed that the implementation currently continues automatically | Treat max-budget as ordinary availability failure |
| 2026-07-28 | Do not calibrate a peer ceiling from input bytes alone | A 15,824-byte pre-implementation Fable request still exceeded a $0.50 ceiling after 115 seconds; reasoning and output behavior materially affect cost | Assume every small plan fits a fixed cheap ceiling; raise the ceiling automatically |
| 2026-07-28 | Invert peer failure handling to a benign-availability allowlist | The current catch-all maps every unknown subtype to process_failure and automatic single-pilot continuation; fixing only error_max_budget_usd would preserve the fail-open class | Add one named subtype to the existing classifier |
| 2026-07-28 | Trigger pre-mutation critique from objective change properties | A packet must not opt out merely by omitting peer convergence from its own declared gates | Let the packet author decide whether critique applies |
| 2026-07-28 | A cheaper post-exhaustion model is advisory only | Model identity is load-bearing for convergence and verification; disclosed downgrade still weakens the gate | Let any successful fallback satisfy the original gate |
| 2026-07-28 | Require a full suite against the final complete candidate fingerprint | Composed proof accelerates intermediate work but is not final acceptance evidence | Compose passing commands from different final-byte states |
| 2026-07-28 | Disable proof reuse on dirty or untracked trees | A complete clean Git tree binds tracked loadable files; untracked conftest/site hooks and unknown environment relationships otherwise escape the fingerprint | Hash only the changed diff |
| 2026-07-28 | Never restart an expired peer lease automatically | A dead local process does not prove the remote paid call stopped; automatic restart can duplicate spend | Permit one implicit restart |
| 2026-07-28 | Persist only screened bounded terminal results outside the repository for at most 24 hours | Recovery needs a short durable window without making peer output an accidental-commit or long-lived content archive | Store results in the worktree indefinitely; store only a digest and lose recovery |
