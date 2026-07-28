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
- [x] Implement frozen snapshot, shadow reduction, and unauthenticated
  controller-asserted profile commit storage.
- [x] Add focused contract, corruption, concurrency, replay, conflict, and
  commit-gate tests.
- [x] Run focused Codex-adapter tests.
- [x] Run broader repository verification appropriate to the changed surface.
- [x] Update verification evidence and disclose all unrun/failed checks.

## Independent Review And Calibration

- [x] Capture and remediate both concrete defects surfaced by failed verifier
  attempts: caller-owned mutable lists and caller-supplied aggregate snapshots.
- [x] Obtain a fresh independent Codex verification against the frozen diff;
  preserve its overall BLOCKED result and candidate-specific invariant passes.
- [x] Obtain Claude architectural/security peer review when usage returns.
- [x] Reconcile every Claude blocker before integration or archive; the final
  review found no candidate-specific blocker.
- [ ] Design routing calibration only after dogfood evidence exists; do not
  invent a scalar score in this packet.

## Accepted Schema-v2 Remediation

- [x] Replace persisted ledger/profile contracts with schema v2 and explicitly
  refuse v1.
- [x] Bound strict JSON depth, integer digits, floats, constants, duplicate
  keys, and millisecond UTC timestamp grammar with boundary tests.
- [x] Deeply detach generic payloads and untrusted nested error claims from
  caller-owned objects.
- [x] Replace idempotency and bare terminal/error names with request-binding,
  trusted-runtime, and explicit untrusted-claim semantics.
- [x] Add explicit token usage, reasoning-token, and cost evidence bases.
- [x] Count one delegation execution once and accept multiple digest-bound
  observations without replaying execution aggregates.
- [x] Persist full replayable submissions plus typed duplicate/conflict
  decisions and durable per-profile rejection counters.
- [x] Enforce the single-writer 30-second lock model, mutation-free reads, full
  observed-stream verification, and qualified sibling imports.
- [x] Require exact canonical JSON serialization plus LF for every observed
  ledger/profile line; block append/commit on byte-equivalent mutations.
- [x] Implement explicit digest-bound torn-tail repair with immutable external
  intent, fsync ordering, atomic replacement, and deterministic crash replay.
- [x] Recompute every intent's before/candidate/completed/later-stream relation
  and require exact selected quarantine metadata before completed replay.
- [x] Support direct source and installed-plugin `scripts/` CLI execution
  through a root-pinned qualified package bootstrap.
- [x] Add strict boundary, same-batch/cross-commit conflict, integration,
  repair fault-injection/replay, and deterministic capacity/performance tests.
- [x] Regenerate the scaffold bundle from fresh LF source and add a direct CRLF
  text-entry rejection invariant as a pre-existing checkout prerequisite.
- [x] Run focused smoke on all three supported local interpreters and the full
  Python 3.11 Codex adapter suite; disclose that Python 3.12/3.14 lack pytest
  and keep independent verification incomplete.

## Accepted Opus-5 Round-1 Remediation

- [x] Replace prefix-only repair with atomic prefix-plus-reserved-marker
  candidates and recompute exact intent/marker/candidate/later-stream
  relations.
- [x] Expose repair-history count/presence, return markers from `read_records`,
  and reserve `drydock_repair` from ordinary append.
- [x] Replace bare `verified` commit-gate naming with unauthenticated
  `controller_asserted_status="passed"` and
  `asserted_verification_ref`; characterize fabricated assertion acceptance.
- [x] Strengthen native contention evidence to 8 subprocesses x 3 appends and
  retain timeout plus OS-handle crash-release proof.
- [x] Freeze serialization, Unicode, binary LF, numeric, capacity, timestamp,
  durability, CI, and global LF-attribute claims in packet text.
- [x] Add the bounded deterministic adversarial corpus without claiming fuzz
  or property-testing coverage.
- [x] Record this slice's final focused command results and diff check.
