# Verification

## Change

backlog-drain

## Automated Checks

- [x] `pytest tests/test_backlog_drain.py tests/test_honest_finish.py tests/test_sdd_gates.py` — **52 passed** (17 drain + 13 honest-finish + 22 existing gates).
- [x] `pytest` (full suite) — **488 passed, 6 skipped**.
- [x] `python scripts/check_sync.py` — OK, 11/11. Real coverage: `scripts/sdd.py` is guarded pair #1, so the scaffold twin is proven byte-identical.
- [x] Every delta requirement and scenario has a named regression test, including the four verifier findings.

## Manual Checks

- [x] **Dogfooded** triage + abandon on a synthetic 3-packet backlog: triage bucketed non-canonical→NEEDS-SYNC, pending-verification→CLAIMED-DONE-UNVERIFIED, pending-tasks→IN-PROGRESS; abandon wrote the honest `Abandoned … never verified` Result + an Override and moved the packet.
- [x] **The verifier confirmed the core safety invariants under adversarial repro**: abandon never fabricates a PASS (template / prior-PASS / no-verification.md), only moves (never deletes), never loses a packet on collision, requires a reason, refuses `--force`; triage is read-only and crash-proof; normal `archive`/`--force` unchanged. All 13 original new tests fail against pre-change `sdd.py` (real invariants).

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| Triage buckets each state | `test_classify_buckets_each_state`, `test_classify_non_canonical_is_needs_sync` |
| Triage robust to a broken packet | `test_classify_missing_file_is_in_progress_not_a_crash`, `test_triage_lists_buckets_and_survives_a_broken_packet` |
| Triage read-only / empty | `test_triage_empty` (+ verifier's before/after tree-hash) |
| Abandon: honest Result, Override, no PASS | `test_abandon_records_absence_never_a_pass` |
| Abandon: only moves, never deletes | `test_abandon_never_deletes_only_moves` |
| Abandon: requires reason; excludes force | `test_abandon_requires_reason`, `test_abandon_and_force_are_mutually_exclusive` |
| **F1** entomb warning covers non-canonical/unattributable | `test_abandon_warns_on_non_canonical_and_unattributable_deltas` |
| entomb warning (canonical) | `test_abandon_warns_when_it_buries_unsynced_spec` |
| **F2** collision leaves packet untouched | `test_abandon_collision_leaves_the_packet_untouched` |
| **F3** stray verdict scrubbed | `test_abandon_scrubs_a_stray_verdict_on_a_malformed_result_heading` |
| **F4** whitespace-only reason refused | `test_abandon_rejects_whitespace_only_reason` |
| result-section swap/append; unsynced list | `test_replace_result_section_*`, `test_unsynced_requirements_lists_absent_ones` |

## Documentation Updates

- [x] `commands/archive.md` — triage + `--abandon` documented (distinct from `--force`, Owner-gated).
- [x] Delta spec `change-packet-gates.md` — triage + abandon requirements, updated for the broadened entomb warning + collision/heading/reason guards.
- [ ] Project context — no change; extends an existing capability.

## Result

**Verified after one adversarial round + fixing all four findings.** The `verifier` returned **VERIFIED WITH NOTES**: md5-frozen tree, every number reproduced (48→52 after the fixes, 484→488 full, 11/11 sync), all normative scenarios pass and fail against pre-change `sdd.py`, core safety holds (never a PASS, only moves, no packet lost on collision, reason required, force excluded), triage read-only and crash-proof.

**All four findings fixed (none blocked archive; fixed for honesty, not because forced):**
1. **[medium] The entomb warning was silent for non-canonical/unattributable deltas** — the exact hole I flagged to the verifier. `_unsynced_requirements` sees only canonical grammar, so abandoning a `### R5 —` or no-`Capability:` delta buried spec knowledge with no warning, while triage/verify are loud about those same deltas. Abandon now also names deltas whose sync it cannot verify. It never fabricated a PASS — an honesty gap, not a safety one.
2. **[low] Abandon wasn't atomic** — it wrote the Result + Override before the collision check, so a clash left a half-abandoned packet and a re-run duplicated the Override. The collision check now precedes any mutation.
3. **[low] A stray verdict on a malformed `## Result: PASS` heading survived** — `_replace_result_section` now matches the heading liberally and rewrites it clean, so no PASS survives an abandon.
4. **[low] Whitespace-only `--reason "   "` was accepted** — now `.strip()`-checked.

**Deferred (unchanged from 0.12.0):** the Stop-time archive-ready nudge (needs the shared-module refactor); the auto-sync writer (Packet B, behind a real-corpus property test). Where abandoned packets live (archive/ vs a distinct dir) remains an Owner decision — they currently go to `archive/`, distinguished by the `Abandoned` Result marker and the Override.
