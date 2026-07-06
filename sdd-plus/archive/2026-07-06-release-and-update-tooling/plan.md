# Plan

## Change

release-and-update-tooling

## Approach

1. **Delta spec** for the new `release-tooling` capability — the version-lockstep, drift-detection, preflight, and print-don't-execute behaviors as SHALL requirements (double as the test plan).
2. **`scripts/release.py`** (stdlib only, Python 3.9+):
   - A single `VERSION_LOCATIONS` table describing each file and how to read/rewrite its version token (JSON key for the two manifests; a line regex for the operator guide `VERSION:` line; presence of a `## <version>` heading for CHANGELOG).
   - `read_versions()` returns the version each location currently declares.
   - `--check` (no bump): print each location's version; exit 0 if all agree and a CHANGELOG entry exists for that version, else exit 1 listing the disagreements. Safe for CI and preflight.
   - `<new-version>`: validate semver-ish and strictly greater than current; rewrite plugin.json + marketplace.json + operator-guide line; require a `## <new-version>` CHANGELOG heading to already exist (fail with a clear message if missing, so the human writes real notes rather than a stub); then run `pytest` and `check_sync.py` via subprocess; on green, print the exact `git add/commit/tag/push` block. Never executes git.
   - `--dry-run`: do everything except write files / run subprocess mutations — prints the intended diffs. (Used to demo without mutating.)
3. **Docs:**
   - Fix `docs/AI_OPERATOR_GUIDE.md:5` `VERSION:` -> current, add a troubleshooting row (stale marketplace clone -> `git -C ~/.claude/plugins/marketplaces/<mp> pull` then reinstall + restart), and a short maintainer subsection pointing at `release.py` and `DEVELOPING.md`.
   - `README.md`: an "Updating" note.
   - `docs/DEVELOPING.md` (new): local dev-install (add the dev repo as a local marketplace source so the plugin runs from the working tree; restart to pick up changes) + the `release.py` release process.
4. **`tests/test_release.py`**: import release.py; assert `read_versions()` on a temp fixture, the bump rewrites exactly the four tokens, `--check` returns nonzero on injected drift and zero when aligned, and semver ordering is enforced. Use temp copies (never mutate the real repo files in tests).
5. **CI:** add a `release.py --check` step.
6. Run the suite; use `release.py --check` to prove it catches the current operator-guide drift; fix the drift; verifier review; sync the delta spec; archive.

## Files Expected To Change

- scripts/release.py (new)
- tests/test_release.py (new)
- docs/AI_OPERATOR_GUIDE.md (VERSION fix + troubleshooting + maintainer note)
- README.md (Updating note)
- docs/DEVELOPING.md (new)
- .github/workflows/ci.yml (add --check step)
- this packet + delta spec

## Risks

- **release.py rewriting the wrong token.** Mitigation: an explicit location table with tight per-file patterns and a test asserting only the four intended tokens change; `--dry-run` shows the diff first.
- **False sense of safety if `--check` isn't wired into CI.** Mitigation: add the CI step in the same change.
- **Local dev-install instructions may vary by Claude Code version.** Mitigation: document the general mechanism (local marketplace source), mark the exact `/plugin` command as "confirm in your terminal", and give the git-pull fallback that we verified works.

## Rollback

All new/edited files are tracked text; `git revert` restores prior state. `release.py` performs no irreversible action (no git execution, no network). Removing it has no runtime effect — it is dev-only tooling not shipped in the scaffold.
