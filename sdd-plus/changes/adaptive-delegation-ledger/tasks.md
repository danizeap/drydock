# Tasks

## Change

adaptive-delegation-ledger

## Architecture

- [x] Confirm FULL scope, primary/supporting skills, and relevant standards.
- [x] Audit the ZeroHandoff reference and separate reusable mechanisms from
  product-specific and overclaimed behavior.
- [x] Define the MVP boundary, non-goals, data flow, permission boundary,
  risks, phases, and testing strategy.
- [x] Write delta requirements before runtime code.

## Implementation

- [x] Implement strict delegation/result/observation/profile contracts.
- [x] Implement the bounded append-only run ledger.
- [x] Implement frozen snapshot, shadow reduction, and verified-only profile
  commit storage.
- [x] Add focused contract, corruption, concurrency, replay, conflict, and
  commit-gate tests.
- [x] Run focused Codex-adapter tests.
- [x] Run broader repository verification appropriate to the changed surface.
- [x] Update verification evidence and disclose all unrun/failed checks.

## Independent Review And Calibration

- [x] Capture and remediate both concrete defects surfaced by failed verifier
  attempts: caller-owned mutable lists and caller-supplied aggregate snapshots.
- [ ] Obtain a fresh independent Codex verification against the frozen diff.
- [ ] Obtain Claude architectural/security peer review when usage returns.
- [ ] Reconcile every Claude blocker before integration or archive.
- [ ] Design routing calibration only after dogfood evidence exists; do not
  invent a scalar score in this packet.

## Accepted Schema-v2 Remediation

- [ ] Replace persisted ledger/profile contracts with schema v2 and explicitly
  refuse v1.
- [ ] Bound strict JSON depth, integer digits, floats, constants, duplicate
  keys, and millisecond UTC timestamp grammar with boundary tests.
- [ ] Deeply detach generic payloads and untrusted nested error claims from
  caller-owned objects.
- [ ] Replace idempotency and bare terminal/error names with request-binding,
  trusted-runtime, and explicit untrusted-claim semantics.
- [ ] Add explicit token usage, reasoning-token, and cost evidence bases.
- [ ] Count one delegation execution once and accept multiple digest-bound
  observations without replaying execution aggregates.
- [ ] Persist full replayable submissions plus typed duplicate/conflict
  decisions and durable per-profile rejection counters.
- [ ] Enforce the single-writer 30-second lock model, mutation-free reads, full
  observed-stream verification, and qualified sibling imports.
- [ ] Implement explicit digest-bound torn-tail repair with immutable external
  intent, fsync ordering, atomic replacement, and deterministic crash replay.
- [ ] Add strict boundary, same-batch/cross-commit conflict, integration,
  repair fault-injection/replay, and deterministic capacity/performance tests.
- [ ] Run focused tests on supported local interpreters and the Codex adapter
  suite if feasible; keep independent verification incomplete.
