# Brief

## Change

release-and-update-tooling

## User Need

Improvements to Drydock only reach users when a correct release is published to GitHub and users refresh their local marketplace clone. Two things repeatedly break that chain, so real work fails to reach anyone: (1) releasing is manual and ad-hoc, so version strings drift and a bump can be forgotten; (2) users have no documented way to force an update when Claude Code's "update" button silently no-ops against a stale marketplace clone.

## Problem

1. **Version drift is structural.** The version lives in four places that are hand-maintained independently: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the `VERSION:` line in `docs/AI_OPERATOR_GUIDE.md`, and a `## <version>` heading in `CHANGELOG.md`. The operator guide's `VERSION:` line is currently `Drydock 0.1.3` while the plugin is `0.1.5` — it drifted again one release after the last hand-fix (v0.1.4 explicitly claimed to fix it). Hand-editing N files will always drift.
2. **No release preflight.** Nothing enforces that tests pass, that `check_sync` is green, or that the four version locations agree before a release goes out. A broken or version-inconsistent release can ship.
3. **Users cannot self-serve an update.** The plugin is installed from a per-user local clone at `~/.claude/plugins/marketplaces/<mp>/`; if that clone is stale (as observed — pinned at v0.1.1, never re-pulled since first install), every reinstall re-copies the old version. There is no troubleshooting entry telling a user how to force-refresh it.
4. **Dogfooding is slow for the maintainer.** Working on Drydock in the dev repo, then testing it as an installed plugin, currently requires the full push -> marketplace-pull -> reinstall round-trip; there is no documented local-dev-install path.

## Scope

In scope:

- `scripts/release.py` — a stdlib-only release helper: `--check` verifies all four version locations agree (for CI + preflight); `<version>` bumps all four in lockstep, runs `pytest` + `check_sync.py`, and prints (never executes) the exact commit/tag/push commands.
- `docs/AI_OPERATOR_GUIDE.md` — fix the stale `VERSION:` line; add a troubleshooting-table entry for "plugin won't update" (stale-clone one-liner); document the release-helper and local-dev-install in a maintainer section.
- `README.md` — short "Updating Drydock" note pointing at the marketplace-update step and the fallback one-liner.
- `docs/DEVELOPING.md` (new) — maintainer guide: local dev-install for instant dogfooding, and the release process via `release.py`.
- `tests/test_release.py` — cover the version-lockstep bump, the drift detector, and the "refuses on inconsistency" behavior.
- `.github/workflows/ci.yml` — add `python scripts/release.py --check` so version drift fails CI.

Out of scope:

- Actually cutting/pushing v0.1.6 (Owner runs the printed git commands).
- Any change to hooks, gates, skills, or the SDD+ lifecycle.
- Auto-updating other users' machines (not possible; not a repo-side action — users pull on their end).

## Acceptance Criteria

- [ ] `release.py --check` detects the current operator-guide drift, then passes once fixed.
- [ ] `release.py 0.1.6` updates all four version locations to 0.1.6 and no others (archive packets, `schema_version`, settings paths untouched).
- [ ] `release.py` refuses (non-zero) if tests or check_sync fail, and prints — never runs — the git publish commands.
- [ ] Operator guide + README carry the stale-clone troubleshooting fix; `DEVELOPING.md` documents local dev-install.
- [ ] CI runs `release.py --check`.
- [ ] pytest green (existing 117 + new release tests); independent verifier review.

## Impact Areas

- Backend: new `scripts/release.py` (dev tooling; not shipped in the project scaffold).
- Frontend: none.
- Data model: none.
- API: none (a CLI dev tool; behavior captured in the delta spec).
- AI/model behavior: none.
- Documentation: operator guide, README, new DEVELOPING.md.
- Operations/security: improves release integrity; no runtime/security surface change. `release.py` prints git commands but never executes network or history-mutating operations.

## Open Questions

- None blocking. `release.py` deliberately does not run git itself (keeps the outward push in the Owner's hands, consistent with this repo's out-of-band commit habit).
