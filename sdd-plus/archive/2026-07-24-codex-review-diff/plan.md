# Plan

## Change

codex-review-diff

## Approach

1. **Discovery** — `changed_files(base)` returns `(files, deleted, error)`:
   - `git diff --name-only -z --diff-filter=ACMRTU <ref>` for changed, `--diff-filter=D` for deleted, `git ls-files --others --exclude-standard -z` for untracked (working-tree mode only). `T` (type change) and `U` (unmerged) are included: a tracked file swapped for a symlink is a type change, and `ACMR` alone filtered it out before the containment guard could see it.
   - Git runs **from the repo root** and paths resolve against it; otherwise a run from a subdirectory drops tracked changes into a false "clean".
   - `-z` (NUL-delimited) because git C-quotes paths with newlines/non-ASCII, which `splitlines()` mangles.
   - A non-zero git return is surfaced as `error`; an invalid `--base` must never read as "clean".
   - `_reviewable()` drops binaries/generated (`.png`, `.lock`, `.min.js`, `.map`, …).
2. **Guards for auto-discovery** (`skip_secret_paths=True`):
   - Name guard: explicit path → refuse; auto-discovered → skip + record in `skipped_secret`.
   - **Repo containment**: an auto-discovered path whose `realpath` is outside `git rev-parse --show-toplevel` is skipped into `skipped_outside_repo` (symlink escape).
   - **Content scan** after the bounded read: high-confidence secret material (PEM private key headers, `sk-`/`ghp_`/`github_pat_`, `AKIA…`, Slack `xox…`, service-account JSON) → refuse (explicit) or skip (auto). The name guard structurally cannot see these.
3. **Prompt hardening** — `_fence()` picks a boundary marker not present in the content (escalating `_1`, `_2`, …), so a file containing the marker cannot close its own delimiter; deleted paths are listed so the reviewer knows what was removed.
4. **CLI** — `--diff` / `--base`; argparse failures emit JSON (`bad_arguments`) instead of bare usage text.
5. Command doc leads with `--diff`; every non-ok stage documented; skips must be surfaced to the Owner.

## Files Expected To Change

- `scripts/conductor/review.py`, `commands/codex-review.md`
- `tests/test_codex_review.py`
- NEW delta `sdd-plus/changes/codex-review-diff/specs/codex-conductor.md`

## Risks

- **Auto-discovery widens what leaves the machine** — the core risk of this feature. Mitigated by three independent guards (name, content, repo containment), each disclosed in the result rather than silent.
- **Content scan is high-confidence-only** — it will not catch every secret shape (a bare hex token in a config, say). It reduces exposure; it does not eliminate it. Stated, not overclaimed.
- **Over-filtering** — a too-aggressive `_SKIP_EXT` would silently drop reviewable files; the list is limited to binary/generated types and the reviewed set is echoed back as `reviewed`.
- **Size caps** — a large change set errors with guidance to narrow, rather than silently truncating.

## Rollback

Additive to `review.py` (explicit-path behaviour unchanged apart from the stronger content guard). `git revert` clean; nothing else depends on `--diff`.
