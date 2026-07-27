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
