# Verification

## Change

codex-review-diff

## Automated Checks

- [x] `pytest tests/test_codex_review.py` — **47 passed, 2 skipped**.
- [x] `pytest` (full suite) — **401 passed, 5 skipped**.
- [x] `python scripts/check_sync.py` — OK: all 11 root/scaffold pairs identical. **This is a null signal for this packet**: `check_sync.PAIRS` covers `sdd.py`, `sdd.ps1`, `CLAUDE.md`, `AGENTS.md` and six templates — none of the three files changed here. Recorded so the green is not mistaken for coverage.
- [x] Every requirement in the delta spec has a named regression test (mapping below), with the **two that cannot execute on this host marked as such** — a passing suite that silently skips a security scenario is exactly the false green this tool exists to prevent.

## Manual Checks

- [x] **Dogfooded on itself, twice.** Round 1: `review.py --diff` reviewed this change and returned **7 findings, all audited as real and fixed** (deleted files dropped, content-secret blindness, symlink escape, git-failure-read-as-clean, C-quoted paths, closable fence, non-JSON argparse exit). Round 2 after the verifier round is recorded under Result.
- [x] **The `delegate_timeout` was found by dogfooding, not by reasoning.** A whole-packet `--diff` did the entire review and then discarded it at the 240s default. `_timeout_for()` now floors at 600s and scales to a 900s cap. The floor carries the weight — a second run proved a size-only bump (245s for a 32KB payload) was still short.
- [x] **The content scanner fired on our own test file** during the dogfood: `tests/test_codex_review.py` contains `sk-`-shaped literals as fixtures, so it landed in `skipped_secret` and was never sent. That is the guard behaving correctly and disclosing it — kept as-is; weakening the pattern to let the fixture through would be the wrong trade.

## Requirement -> Test Mapping

| Requirement | Test |
| --- | --- |
| R26 discovery (modified + untracked) | `test_changed_files_finds_modified_and_untracked` |
| R26 type change (`T`) not dropped | `test_type_change_is_discovered_not_dropped` — **SKIPPED on this host** (needs symlink privilege); unproven here |
| R26 unmerged (`U`) not dropped | `test_unmerged_files_are_discovered` (real merge conflict; runs) |
| R26 binary/generated exclusions disclosed | `test_unreviewable_files_are_disclosed_not_dropped` |
| R26 no false clean from a subdirectory | `test_changed_files_from_subdirectory_still_sees_root_changes` |
| R26 binaries/generated excluded | `test_changed_files_skips_binaries_and_generated` |
| R26 deletions reported | `test_changed_files_reports_deletions` |
| R26 git failure != clean | `test_invalid_base_is_an_error_not_clean` |
| R27 secret by name: auto-skip vs explicit-refuse | `test_auto_discovery_skips_secret_but_reviews_rest`, `test_review_refuses_secret` |
| R27 secret by content (incl. UTF-16) | `test_content_secret_refused_for_explicit_path`, `test_content_secret_skipped_in_auto_discovery`, `test_utf16_secret_still_caught` |
| R27 modern key formats (`sk-proj-`, `sk-ant-`, …) | `test_hyphenated_and_underscored_api_keys_are_caught` (4 params) |
| R27 disclosure survives a pre-fleet failure | `test_discovery_failure_still_discloses_deletions` |
| R27 size/content from one handle | `test_file_growing_during_read_cannot_beat_the_cap` (fstat branch), `test_hard_capped_read_catches_growth_after_the_stat` (capped-read branch) |
| R27 repo containment | `test_symlink_outside_repo_is_skipped` — **SKIPPED on this host** (needs symlink privilege). The verifier exercised the branch independently without a symlink (out-of-repo absolute path, and a prefix-collision sibling `…/repo-evil/x.py`); both landed in `skipped_outside_repo`, so the guard is real — only the symlink route is unproven here |
| R27 deleted secret names withheld from the reviewer | `test_deleted_secret_paths_are_not_named_to_the_reviewer` |
| R27 prompt paths carry no local identity | `test_paths_sent_to_the_reviewer_are_repo_relative` |
| R27 fail closed with no repo root | `test_auto_discovery_fails_closed_without_a_repo_root` |
| R27 **no skip is silent, even on failure** | `test_skips_are_disclosed_even_when_the_run_fails_early` |
| R27 missing file skipped, not fatal | `test_missing_file_is_skipped_not_fatal_in_auto_discovery` |
| R27 everything filtered | `test_auto_discovery_all_secret_sends_nothing` |
| R28 fence escalates on content | `test_fence_marker_escalates_so_content_cannot_close_it` |
| R28 fence escalates on **path** | `test_fence_marker_escalates_for_a_marker_bearing_PATH` |
| R28 deleted paths are data | `test_deleted_paths_are_data_not_instructions` |
| R28 `--base` argument injection | `test_option_shaped_base_is_rejected_before_reaching_git` |
| R28 all-JSON CLI contract | `test_main_no_paths_...`, `test_main_bad_flag_...`, `test_main_diff_outside_a_repo_...`, `test_main_diff_clean_tree_...`, `test_main_diff_only_deletions_...`, `test_main_diff_reviews_changed_files` |
| R28 nothing on stderr | `test_main_argparse_writes_nothing_to_stderr` |
| R28 ambiguous flag combos refused | `test_main_rejects_diff_with_paths`, `test_main_rejects_base_without_diff` |
| R28 every CLI stage carries the lists | `test_main_error_stages_carry_the_disclosure_keys` |

## Documentation Updates

- [x] `commands/codex-review.md` — `--diff` leads as the pre-`verify` step; `no_repo_root` documented; skip lists stated as present on **every** outcome including failures.
- [x] Delta spec `specs/codex-conductor.md` — R27/R28 tightened to match what is actually enforced (fail-closed containment, path-borne fence, delimited deleted paths, ref validation).
- [ ] Project context — no change needed; this adds a flag to an existing capability.

## Result

**Verified after two adversarial rounds.** The first `verifier` pass returned **NOT VERIFIED** against this packet's own normative text, with runnable repros. All blocking findings are fixed and each carries a regression test:

1. **R27 violated — skips were silent on failure.** `skipped_secret` / `skipped_outside_repo` / `deleted` were dropped on the `too_large`, `missing_file` and `read_error` returns, so a run that declined to send a `.env` could report only `too_large`. This was a declared stop condition in `brief.md`. Fixed by accumulating into a single `ctx` spread into **every** return.
2. **R28 violated — the fence was escapable by path.** The marker was computed over content only while paths were interpolated into the BEGIN line, so a filename containing the marker closed its own fence; deleted paths sat in the instruction region entirely undelimited. Fixed: the marker is computed over content **and** paths **and** deleted paths, and deleted paths moved inside a delimited region.
3. **R26's false clean was still reachable.** Git lists paths repo-root-relative while `isfile()` resolved against the CWD, so running from a subdirectory silently dropped tracked changes into "no changes" — with no git error to hint at it. Fixed: git runs from the repo root and paths resolve against it.
4. **Containment failed open.** With no repo root, auto-discovery proceeded; now it refuses (`no_repo_root`), matching `guard_outbound`'s fail-closed posture.
5. **`--base` reached a git argv unvalidated** — `--output=<path>` made git write an arbitrary file. Argument injection; now rejected before git runs.
6. **`main()` had zero coverage.** Six CLI tests added.

**Round 3 — Codex's own review of the fixed code returned six findings, all confirmed real and fixed:**

1. **HIGH — the secret regex was effectively dead for current keys.** `sk-[A-Za-z0-9]{20,}` stops at the first hyphen, so it matched the legacy format and missed `sk-proj-…` and `sk-ant-…`. It caught the rare case and passed the common one. Now `[A-Za-z0-9_-]`, with four parametrised regressions.
2. **`--diff-filter=ACMR` dropped type changes (`T`) and unmerged (`U`).** A tracked file replaced by a **symlink** is a type change — the exact case repo-containment exists to catch — filtered out before the guard could see it. Now `ACMRTU`.
3. **Disclosure was still incomplete.** `review()` returned the `discover` stage before `ctx` existed, and `main()`'s stages emitted bare dicts. `ctx` is now built first and every CLI stage goes through `_emit_stage()`.
4. **stat-then-open TOCTOU on size.** Size and content now come from one handle (`os.fstat` on the open fd) with a hard-capped read.
5. **Ambiguous flag combos silently dropped scope** (`--diff` with paths; `--base` without `--diff`). Both are now `bad_arguments`.
6. **argparse wrote usage to stderr before the JSON.** A caller merging streams got non-JSON from an all-JSON contract. `_QuietParser.error()` raises without printing.

**Round 4 — the `verifier` returned VERIFIED WITH NOTES with three archive blockers, all now closed:**

1. **F2, a literal R27 violation nobody had noticed across three rounds.** Deleted *path names* never passed the name guard, so a deleted `.env` or `id_rsa` was named to Codex. R26 ("name the deleted paths") and R27 ("never send a secret-bearing path") contradicted each other and the code obeyed only R26. Resolved in R27's favour: the prompt is filtered, the Owner still sees the full `deleted` list, and the divergence is documented in the command doc.
2. **F5 — `commands/codex-review.md` predated the behaviour change** and documented neither `bad_arguments` nor the flag-combo refusals, while `verification.md` ticked it as done. Fixed.
3. **F6 — the packet contradicted itself**: `tasks.md` still claimed 31/384 and `plan.md` still specified `ACMR`. Both corrected.

Also fixed from the same pass: **F4**, binary/generated exclusions were a genuinely silent skip (now `skipped_not_reviewable`); **F3**, absolute paths shipped `C:\Users\<name>\…` off-machine on every `--diff` (prompt paths are now repo-relative); **F9**, an unsafe `--base` was reported as `git_error` when git was never reached (now `bad_arguments`); **F7**, the hard-capped-read branch had no executing test.

**Process failure, mine.** I edited `review.py`, the tests, and the normative spec *while the verifier was reading them*. It caught this itself, pinned file md5s, and re-ran everything against a stable snapshot — but it nearly reported findings against code that no longer existed. A verifier must be given a frozen tree; running one against a moving target risks a verdict that describes nothing.

**Round 5 — confirmation pass on a frozen tree: VERIFIED WITH NOTES, no blocker remaining.** File md5s were identical at start and end, so every finding describes code that still exists. All three blockers confirmed closed under the verifier's own repros (the F2 probe built the actual prompt and showed `.env`, `id_rsa` and `src/config/.env.production` absent from it while all four deletions remained in the Owner's list). `_display()` was probed on 13 edge cases including the prefix-collision trap `…/drydock-evil/x.py`; real-path reads and display paths are not crossed anywhere. Four commands re-run, all matching.

One item it flagged as **fix-before-sync**, now fixed: R26's scenario text still read "named to the reviewer" with no carve-out, and `/drydock:sync` would have written that sentence into the living capability spec as a normative requirement the shipped code deliberately violates — the F6 failure mode one file over. Also fixed from the same pass: the `no_changes`/`only_deletions` stages emitted absolute paths against a doc promising repo-relative (no test caught it because the CLI assertions compare basenames — now `test_cli_stages_report_repo_relative_paths`); `guard_outbound`'s second probe element was a CWD-resolved path that would silently mis-resolve if that guard ever became directory-aware; and `docs/AI_OPERATOR_GUIDE.md` still described the command as file-only with no mention of `--diff`.

**What this packet actually demonstrates.** The two reviewers found **near-disjoint** defect classes: the `verifier` subagent found spec violations (silent skips on failure, path-borne fence escape, subdirectory false-clean, fail-open containment) and Codex found implementation gaps (dead regex, filter seam, stderr leak, TOCTOU). Round 1's verifier read this file four times without noticing the regex was dead for modern keys; more rounds of one vantage does not become a second vantage. That is the empirical case for cross-model review as a rung in `/drydock:verify`.

**Known and accepted limits** (stated, not overclaimed): the content scan is high-confidence patterns only and will not catch every secret shape; a hardlink can defeat realpath containment; a symlink swap between the containment check and `open()` remains a narrow TOCTOU window (there is no portable `O_NOFOLLOW` on Windows). The mitigation for all three is that Codex runs read-only and receives only what survives the guards.
