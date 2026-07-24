# Verification

## Change

honest-finish

## Automated Checks

- [x] `pytest tests/test_honest_finish.py tests/test_sdd_gates.py` — **35 passed** (13 honest-finish + 22 existing gate tests, all preserved).
- [x] `pytest` (full suite) — **471 passed, 6 skipped**.
- [x] `python scripts/check_sync.py` — OK, 11/11. Here the green is **real coverage**: `scripts/sdd.py` is guarded pair #1, so the scaffold twin is proven byte-identical.
- [x] Every delta requirement and scenario has a named regression test; the deferred archive-grammar boundary is pinned by a test.

## Manual Checks

- [x] **Dogfooded the prompt** on throwaway packets: non-canonical delta → grammar warning + "not machine-verifiable, run /drydock:sync"; canonical + synced → `READY TO ARCHIVE`; canonical + unsynced → "Nearly there, run /drydock:sync". And on this packet itself while incomplete → correctly silent (not green).
- [x] **No living-spec write**: the verifier traced every write path from verify/archive — verify writes nothing; archive only appends to the packet's own decision-log (override) and `shutil.move`s the packet. Nothing touches `sdd-plus/specs/capabilities/`.
- [x] **Behavior preservation**: the verifier confirmed archive still blocks each of the four gates without `--force` and records the real blockers with it; the hard missing-artifact exit still fires and is non-waivable. Existing `test_sdd_gates.py` all pass.

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| R1 shared readiness, prompt & gate agree on structural blockers | `test_readiness_empty_for_a_clean_synced_packet`, `test_readiness_flags_canonical_but_unsynced`, `test_readiness_flags_pending_and_unfilled` |
| R2 ready prompt fails toward needs-sync (READY / nearly / refuses) | `test_prompt_says_ready_when_green_and_synced`, `test_prompt_says_nearly_there_when_canonical_but_unsynced`, `test_prompt_refuses_ready_on_non_canonical_delta`, `test_prompt_silent_when_tasks_pending` |
| R2 archive warned-but-permissive on grammar (deferred boundary) | `test_archive_warns_but_proceeds_on_non_canonical` |
| R3 delta grammar lint | `test_lint_flags_non_canonical_requirement_heading`, `test_lint_accepts_canonical_and_ignores_scenarios`, `test_lint_ignores_headings_outside_added` |
| unified done-predicate | `test_packet_unfilled_detects_pending_result` |
| archive behavior preserved (block → force-waive) | `test_archive_blocks_unsynced_then_force_waives` + `test_sdd_gates.py` |

## Documentation Updates

- [x] `commands/verify.md` — the ready line, its fail-toward-sync guarantee, and the archive-permissive-on-grammar note.
- [x] Delta spec `change-packet-gates.md` — R1–R3 plus the archive-grammar-boundary scenario.
- [ ] Project context — no change; extends an existing capability.

## Result

**Verified after one adversarial round + an overclaim fix.** The `verifier` returned **VERIFIED WITH NOTES**: md5-frozen tree, every number reproduced exactly (34→35 after the fix, 470→471 full, 11/11 sync), all three requirements implemented with regression tests that fail against pre-change `sdd.py` (11 of 12 originally; the pinning test added this round makes the deferred boundary explicit), behavior preserved, no living spec written, twin byte-identical, and the false-READY hole genuinely closed at the verify prompt.

**Finding 1 (medium) — the overclaim — fixed.** I had claimed the prompt and gate "can never disagree" and that the "archive clean" half of the hole was closed. Neither is literally true: verify's prompt refuses READY on non-canonical grammar, but `archive` warns and *proceeds* (no block, no override). This is spec-compliant (Req 1 defines exactly four blockers; grammar isn't among them) and was a deliberate WARN-not-REJECT deferral — but the docs and test docstring said more than the code delivers, which is the exact recurring failure mode of this session. Fixed by (a) correcting the test docstring and the brief/verify.md framing to state the prompt is deliberately *stricter* than the gate on grammar, (b) recording the asymmetry as a decision, and (c) **pinning** archive's warn-but-proceed behavior with `test_archive_warns_but_proceeds_on_non_canonical` so the deferred boundary is tested, not just asserted. Finding 2 (the docstring) is subsumed by the same fix.

**Explicitly deferred (stated, not hidden):** making `archive` also fail toward needs-sync on grammar is a soft-REJECT that would force `--force` or canonical authoring on every archive — an Owner decision. The auto-sync writer (the one path that could corrupt a living spec) is Packet B behind a real-corpus property test. The Stop-time archive-ready nudge (reaching the operator who never runs verify) is 0.12.1, after `archive_readiness` is extracted into the shared hook module.
