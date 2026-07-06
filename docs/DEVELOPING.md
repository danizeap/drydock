# Developing Drydock

This guide is for people **working on the Drydock plugin itself** (not for using it in a project — that's the README and `AI_OPERATOR_GUIDE.md`).

## How updates actually reach users

Drydock is distributed as a GitHub-sourced Claude Code marketplace (`danizeap/drydock`, `source: "./"`). There is **no central registry** — the GitHub repo *is* the marketplace. On each user's machine the flow is three hops:

```
GitHub (danizeap/drydock)                 <- you push here = "published"
  -> ~/.claude/plugins/marketplaces/drydock/   (a per-user git CLONE)
    -> ~/.claude/plugins/cache/drydock/drydock/<version>/   (the installed plugin)
```

Key consequence: **pushing a release does not reach anyone automatically.** Each user updates on their side, and the update only works if their *marketplace clone* gets `git pull`-ed. If it doesn't, reinstalling just re-copies the old version from the stale clone (this is a real gotcha — it hid four releases once).

### If an update won't take (stale clone)

```
/plugin marketplace update drydock          # the intended refresh (git pull the clone)
# if the button/command silently no-ops:
git -C ~/.claude/plugins/marketplaces/drydock pull   # do it by hand
# then reinstall the plugin and RESTART the session (hooks load at session start)
```
Confirm success: `~/.claude/plugins/cache/drydock/drydock/` should show the new `<version>/` folder.

## Local dev-install (instant dogfooding)

Round-tripping your own changes through GitHub -> marketplace-pull -> reinstall is slow. To run the plugin **directly from your working tree** so changes are live on the next restart, add your local repo as a marketplace source:

```
/plugin marketplace add <absolute-path-to-your-drydock-checkout>
/plugin install drydock@drydock
```

The repo's `.claude-plugin/marketplace.json` already declares `source: "./"`, so a local add points the plugin at your working tree. Restart to pick up edits (hooks and plugin metadata load at session start).

> Confirm the exact `/plugin` syntax for your Claude Code version — the marketplace/plugin management commands are interactive and evolve. If a local `drydock` marketplace name collides with the GitHub one, remove the GitHub marketplace first (or add the local one under a distinct name). The `git -C ... pull` fallback above always works regardless.

## Releasing

Use the release helper — it keeps the version in lockstep across the four places it's declared and gates the release on the tests. It **never runs git**; it prints the commands for you.

```
python scripts/release.py --check          # verify all version locations agree (also runs in CI)
python scripts/release.py <version> --dry-run   # preview the bump, write nothing
python scripts/release.py <version>        # bump + run pytest & check_sync, then print git commands
```

Steps for a release:

1. Write real notes under a new `## <version>` heading in `CHANGELOG.md` (the helper refuses to bump without it).
2. Run `python scripts/release.py <version>`. It rewrites `plugin.json`, `marketplace.json`, and the `VERSION:` line in `AI_OPERATOR_GUIDE.md`, then runs the test suite and `check_sync.py`.
3. Run the `git commit` / `git tag` / `git push` block it prints. Pushing to `main` is what publishes the release.
4. Update your own installed copy (see stale-clone note above) and restart to dogfood it.

### Where the version lives

`release.py` owns these four locations — don't hand-edit them individually:

- `.claude-plugin/plugin.json` (`version`)
- `.claude-plugin/marketplace.json` (plugin `version`)
- `docs/AI_OPERATOR_GUIDE.md` (`VERSION:` line)
- `CHANGELOG.md` (`## <version>` heading — you write this)

## Tests, CI, and the dual-copy invariant

- `python -m pytest tests/` — hooks, packet gates, and the release helper.
- `python scripts/check_sync.py` — the root files that ship to new projects (under `assets/project-scaffold/`) must stay byte-identical to their root copies; when you edit a guarded file, `cp` it over the scaffold copy and re-run. `.gitattributes` pins LF so the parity is stable cross-platform.
- CI (`.github/workflows/ci.yml`) runs pytest, `check_sync`, and `release.py --check` on Ubuntu + Windows across Python 3.9 and 3.12. Version drift now fails the build.
- `scripts/release.py` is **dev-only** and is deliberately not shipped in the project scaffold — downstream projects have their own release process.
