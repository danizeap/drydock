# Verification

## Change

adaptive-delegation-ledger

## Evidence Before This Opus-5 Round-1 Slice

- [x] Python 3.11 Codex adapter suite: 227 passed, 2 skipped.
- [x] Python 3.11 legacy `tests/` suite: 548 passed, 6 skipped.
- [x] LaunchGuardian reviewed-source strict scan:
  `APPROVED_WITH_DISPOSITIONS`; all five scanners participated and there were
  0 open blockers.
- [x] Python 3.12 and 3.14 received direct CLI/adversarial smoke only because
  `pytest` was absent in those interpreter environments. No Python 3.12/3.14
  pytest count is claimed.

These are pre-slice facts supplied for correction of stale packet text. They
were not rerun by this bounded worker.

## This Slice: Exact Local Commands And Results

- [x] Final syntax check:
  `python -m py_compile adapters/codex/drydock/scripts/delegation_contracts.py adapters/codex/drydock/scripts/delegation_ledger.py adapters/codex/drydock/scripts/capability_profiles.py adapters/codex/tests/test_delegation_contracts.py adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py`.
  Exit 0 with no output.
- [x] Final focused suite:
  `python -m pytest adapters/codex/tests/test_delegation_contracts.py adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py -q`
  on Python 3.11.9: 120 passed in 10.75s.
- [x] `python scripts/sdd.py verify adaptive-delegation-ledger`: exit 0;
  `Verified artifacts for adaptive-delegation-ledger. Tasks: 33 complete, 5
  pending. Pending tasks remain. Archive will require --force.`
- [x] `git diff --check`: exit 0 with no output.

Development-only runs, retained rather than laundered into the final pass:

- `py -3.11 -m py_compile adapters/codex/drydock/scripts/delegation_ledger.py adapters/codex/drydock/scripts/capability_profiles.py adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py; py -3.11 -m pytest adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py -q`
  did not start:
  the Windows launcher returned `No installed Python found!`; the available
  `python` command was then confirmed as Python 3.11.9.
- `python -m py_compile adapters/codex/drydock/scripts/delegation_ledger.py adapters/codex/drydock/scripts/capability_profiles.py adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py; python -m pytest adapters/codex/tests/test_delegation_ledger.py adapters/codex/tests/test_capability_profiles.py adapters/codex/tests/test_delegation_integration.py -q`
  completed syntax compilation, then reported 21 failed and 67 passed. The
  failures exposed the marker occupying the torn record's sequence and a
  Windows locked-file test reading the sidecar before releasing its own lock;
  both were corrected.
- Rerunning the same three-module pytest command reported 1 failed and 87
  passed. The remaining test mutated the candidate rather than the later
  appended suffix; the fixture was corrected to exercise the intended later
  stream.
- A subsequent four-module run passed 120 tests in 10.39s. The next rerun
  after contention start-gate/cleanup hardening passed 120 in 10.80s. The
  cross-platform `r+b` existing-file handle alignment rerun passed 120 in
  10.44s. The final rerun above adds the explicit all-child-exits assertion and
  supersedes those timings.

## Pilot Acceptance After The Worker

- [x] Targeted lock/repair boundary selection:
  `python -m pytest adapters/codex/tests/test_delegation_ledger.py -q -k
  "eight_processes or final_record_capacity or repair_replays or
  repair_event_type_is_reserved"` on Python 3.11.9: 8 passed, 54 deselected in
  7.40s.
- [x] Full Codex adapter suite on Python 3.11.9:
  `python -m pytest adapters/codex/tests -q`: 244 passed, 2 skipped in 82.78s.
- [x] Legacy suite on Python 3.11.9:
  `python -m pytest tests -q`: 548 passed, 6 skipped in 44.95s.
- [x] Current-candidate direct CLI plus typed adversarial scanner smoke passed
  on Python 3.12 and 3.14. `python -m pytest --version` failed on each with
  `No module named pytest`; those environments were not modified.
- [x] `python scripts/check_sync.py`: all 11 root/scaffold pairs identical.
- [x] Deterministic scaffold-bundle, generated-hook, and release-version
  checks passed. All version locations remain 0.12.1; no release was made.
- [x] `git diff --check`: exit 0 with no output.

## Existing CI Evidence Path

- [x] Read-only inspection confirms `.github/workflows/ci.yml` already runs
  `python -m pytest tests/ -q` and
  `python -m pytest adapters/codex/tests/ -q` on `ubuntu-latest` and
  `windows-latest` with Python 3.9 and 3.12.
- [x] No redundant CI workflow was added.
- [x] Read-only inspection confirms the global `.gitattributes` rule
  `* text=auto eol=lf` already covers source and generated bundle text; no
  duplicate bundle-specific rule was added.

CI is the Windows/POSIX Python 3.9/3.12 evidence path. The local commands above
are separate implementer evidence and do not claim that CI ran for this diff.

## Behavior Proven By Focused Tests

- [x] Atomic repair installs the valid prefix plus the exact reserved
  `drydock_repair` marker, including at the injected post-replace crash
  boundary.
- [x] A repair marker may occupy record 10,000. The resulting ledger verifies,
  exposes one repair-history record, and then hard-refuses another append at
  the record ceiling.
- [x] The marker binds before digest, discarded-tail digest/count,
  classification, prefix record/byte counts, extractable sequence,
  before-digest-derived intent identity, and optional quarantine reference,
  without raw tail bytes.
- [x] `verify` exposes `repair_history_count` and `has_repair_history`;
  `read_records` returns the marker; ordinary `RunLedger.append` refuses its
  reserved event type.
- [x] Before, prepared-candidate, completed, quarantine, marker-tamper, and
  later-stream replay relations are recomputed; no candidate-digest-only
  completion shortcut remains.
- [x] Eight real OS subprocesses append three events each. All children exit
  zero; 24 IDs and sequences are unique, sequences are contiguous, all 24
  lines are exact canonical JSON plus LF with no torn bytes, and final chain
  verification succeeds.
- [x] Lock contention times out through the monotonic caller bound; terminating
  the lock owner releases the OS lock; reacquisition succeeds; the racing-open
  sidecar contains exactly one initialization byte and uses no PID file.
- [x] A fabricated `controller_asserted_status="passed"` plus nonexistent
  `asserted_verification_ref` is accepted when structural/state gates pass.
  The store establishes no evidence existence/origin, actual pass result,
  independent process, permission, or authority.
- [x] The deterministic adversarial corpus covers braces/quotes in strings,
  escaped quotes, truncated escapes, Unicode escape/surrogate truncation,
  nested arrays, and mid-file malformation refusal. It is deterministic corpus
  evidence, not fuzz/property proof.
- [x] Canonicalize-parse-canonicalize is stable for the corpus, and composed
  versus decomposed Unicode remains distinct without normalization.

## Backend Evidence

- Classification: local data mutation and agent-orchestration substrate.
- Function inventory: immutable contract constructors/parsers; one run-ledger
  append/read/verify/explicit-repair boundary; pure profile shadow reducer; one
  optimistic profile commit/read/verify boundary.
- Inputs and validation: exact schemas, duplicate-key and non-finite refusal,
  identifier/reference/timestamp/digest validation, byte/depth/count/integer
  bounds, secret-shaped value checks, and forbidden raw-content field names.
- Auth/authorization: no network route, account, credential, tenant, or remote
  authorization surface is added. Controller assertions are unauthenticated
  and learned data grants no effect authority.
- Mutation safety: sidecar OS locking with byte-zero initialization, full existing-stream
  verification before mutation, contiguous allocation under lock,
  append/flush/fsync, immutable external repair intent, optional quarantine,
  atomic prefix-plus-marker replacement, exact crash replay, optimistic state
  digest, and exact source recomputation.
- Lock contract: writer `a+b`; existing-file reader `r+b` without writes on
  both OS paths; `seek(0)`; custom nonblocking `msvcrt.LK_NBLCK` on the one-byte Windows range
  at byte zero; `fcntl.flock(..., LOCK_EX | LOCK_NB)` on the whole POSIX
  sidecar; 25 ms retry; monotonic caller timeout capped at 30 seconds;
  initialization under the selected acquired lock; OS close/crash release; no
  stale PID policy and no cross-OS semantic-identity claim.
- Serialization/I/O: `sort_keys=True`, compact comma/colon separators,
  `ensure_ascii=True`, `allow_nan=False`, exact code points without Unicode
  normalization, finite bounded Python numerics, binary I/O, and exactly one
  LF. No cross-language canonicalization claim is made.
- Durability/timestamps: files are flushed and file-fsynced. Parent-directory
  fsync is performed on POSIX and unavailable in this Windows stdlib path, so
  equal power-loss durability is not claimed. Default timestamps use the OS
  UTC wall clock to milliseconds; accepted caller timestamps follow the same
  exact grammar and need not be monotonic.
- Capacity: run ledger hard-refuses beyond 10,000 records, 16 MiB total, or
  32 KiB per line. Profile history hard-refuses beyond 32 commits or 64 source
  submissions per commit (plus its documented byte/profile ceilings).
- Integration behavior: no provider call, credential access, scheduler,
  permission change, or live adapter integration occurs in this packet.
- Kill switch/rollback: live behavior has no switch because it is not wired.
  Deliberate rollback reverts the additive runtime/tests and rebuilds the
  consumed generated bundle from the intended reverted scaffold source; it
  does not delete the bundle artifact.

## Documentation And Review Gates

- [x] Delta spec, plan, Build Blueprint, decision log, tasks, and verification
  updated for the accepted round-1 remediation.
- [x] Fresh independent verifier reviewed exact commit `cefc2ea`. Its overall
  result remains BLOCKED because both mandatory pytest commands were nonzero.
  It nevertheless reported every candidate-specific invariant PASS and
  `implementation_defects: []`. The exact structured result is preserved in
  `codex-final-verifier.json`; the failures are not relabelled as passes.
- [x] Claude reviewed `7d4c08b..cefc2ea` read-only from an extracted candidate
  tree, reproduced 126/1 focused, 244/2 adapter, and 548/6 legacy counts, and
  returned `converged: true` with no candidate blocker. Its structured result
  is preserved in `claude-final-review.json`.
- [x] Claude classified the verifier's 13 hook-runtime failures as the
  unchanged `py -3` launcher dependency and the one descendant-cleanup failure
  as a separate unchanged timing-sensitive runner issue. Those remain tracked
  gaps rather than candidate passes.
- [x] Two earlier automated peer attempts are operational failures, not
  reviews: Opus 5 and Fable 5 each received the bounded 297 KB source packet
  and exited with `error_max_budget_usd` under a $1 controller ceiling.
- [ ] Live controller/executor integration.
- [ ] Living spec sync and archive.
- [x] Candidate and review evidence committed; checkpoint branch pushed; Owner
  branch fast-forwarded without reconstructing the reviewed commits.
- [ ] Install, release, archive, or deployment.

## Final Owner-Branch Integration Evidence

- [x] `codex/adaptive-delegation-ledger` fast-forwarded from `7d4c08b` through
  the three reviewed implementation commits and evidence-only commit
  `e724052`.
- [x] Integrated adapter run reached 243 passed/2 skipped and one deterministic
  bundle failure caused by seven pre-existing CRLF working-tree files. No
  candidate behavior test failed.
- [x] The seven scaffold files and their two authoritative root peers were
  normalized in the working tree to the LF bytes already stored in Git. This
  produced no staged content change. The failed bundle module then passed
  5/1, and the deterministic bundle check passed.
- [x] Integrated legacy suite:
  `python -m pytest tests -q -p no:cacheprovider` reported 548 passed/6 skipped
  in 53.53 seconds.
- [x] Root/scaffold parity, deterministic bundle, generated hook definition,
  release-version parity, packet structure, and `git diff --check` all passed.
- [x] The final working tree was clean. Evidence is intentionally combined
  rather than rerunning the 243 already-passing adapter tests after an
  LF-only working-tree correction.

## Result

CANDIDATE-SPECIFIC CODE CONVERGENCE ESTABLISHED; FULL REPOSITORY VERIFICATION
REMAINS BLOCKED BY THE DISCLOSED ENVIRONMENTAL AND UNCHANGED RUNNER FAILURES.
The substrate is not wired into live routing, is not archive-ready, and
carries no install, launch, release, or deployment authorization. Claude also
identified a pre-existing quadratic append curve, unlocked reads when the
sidecar is absent, and an unverified write-denied-storage boundary; these are
non-blocking follow-up gaps, not erased evidence.
