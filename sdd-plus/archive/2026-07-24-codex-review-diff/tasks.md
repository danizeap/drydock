# Tasks

## Change

codex-review-diff

## Implementation

- [x] `changed_files(base)` — NUL-delimited git listing (changed + untracked + deleted), git failure surfaced as an error, binaries/generated filtered.
- [x] `review.py --diff [--base <ref>]`; explicit paths still supported; all-JSON contract on argparse failure.
- [x] Auto-discovery guards: secret-by-name skipped+disclosed (explicit still refused), **content-level** secret scan, **repo containment** for symlinks.
- [x] Prompt hardening: escalating boundary marker content cannot close; deleted paths listed for the reviewer.
- [x] `commands/codex-review.md` — `--diff` leads as the pre-`verify` step; every non-ok stage and every skip list documented.
- [x] **Dogfooded on itself**: `review.py --diff` reviewed this change and returned 7 findings; all audited as real and fixed (deleted-files dropped, content-secret blindness, symlink escape, git-failure-as-clean, C-quoted paths, closable fence, non-JSON argparse exit).
- [x] `tests/test_codex_review.py` — discovery (modified/untracked/deleted/binaries), invalid base = error, content-secret refuse+skip, symlink-outside-repo skip, fence escalation, auto-skip vs explicit-refuse.
- [x] **Verifier round 2 fixes** (first pass returned NOT VERIFIED against our own R26/R27/R28): skips disclosed on every failure return; fence computed over paths too and deleted paths delimited; git listing resolved repo-root-relative so a subdirectory cannot report a false clean; containment fails closed with no repo root; `--base` validated before reaching a git argv; `missing_file` skipped rather than fatal in auto-discovery; UTF-16 secrets caught; `main()` covered.
- [x] `_timeout_for()` — dogfooding hit `delegate_timeout` at the 240s default *after* doing the whole review; floor raised to 600s, scaling to a 900s cap.
- [x] **Codex round-3 review fixes** (6/6 confirmed real): secret regex was dead for `sk-proj-`/`sk-ant-` keys (high); `--diff-filter` dropped type changes and unmerged; disclosure keys missing from the pre-fleet failure and CLI stages; stat/open TOCTOU on size; ambiguous flag combos silently dropping scope; argparse leaking usage to stderr ahead of the JSON.
- [x] **Verifier round-3 fixes**: deleted secret-bearing path *names* were still sent to the reviewer (literal R27 violation) — now filtered from the prompt while the Owner still sees the full `deleted` list; binary/generated exclusions surfaced as `skipped_not_reviewable` instead of vanishing; prompt paths made repo-relative so `C:\Users\<name>\…` stops leaving the machine; an unsafe `--base` now reports `bad_arguments` rather than `git_error` (git was never reached).
- [x] **Round-5 pre-sync fixes**: R26's scenario text still promised deleted paths are named to the reviewer unconditionally — sync would have written a requirement the code intentionally violates into the living spec; CLI early stages emitted absolute paths; operator guide had no `--diff`.
- [x] Run verification — review suite **47 passed, 2 skipped** (both need symlink-creation privilege on this host); full suite **400 passed, 5 skipped**; check_sync 11/11; `verification.md` filled with the requirement->test map; `verifier` subagent across three rounds; Codex cross-review at round 3.
