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
