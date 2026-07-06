# Changelog

## 0.2.0 — autopilot floor

Moves lifecycle *orientation* and *override governance* into the deterministic tier, so the agent is self-aware of project state and the guardrails prove themselves every session — the foundation for a protocol that governs itself. Shipped through Drydock's own lifecycle (third dogfood).

- **`SessionStart` orientation hook (`hooks/session_orient.py`).** Read-only; fires every session; **silent outside a Drydock project** and **always exits 0** (it can only add context, never block or slow a session). In a Drydock project it injects state — PROJECT_CONTEXT filled/template/missing, active packets, pending tasks, unfilled verification — and a **guardrail liveness verdict** (probes `git_safety`/`protect_secrets` under this interpreter; "live" only on a genuine block + benign control + expected message; plus a static `hooks.json` wiring check). Designed against an adversarial red-team: bounded project discovery (never orients on a foreign or template repo), untrusted-`cwd` handling, `except BaseException` (SystemExit-safe), and derived-signals-only output (no file content or absolute paths).
- **Governed `--force`.** `sdd.py archive --force` now requires `--reason "<why>"` and appends an auditable override record (date, gate(s) waived, reason) to the packet's `decision-log.md`, which travels into `archive/`. Bare `--force` is refused.

## 0.1.6 — release & update tooling

Makes publishing reliable and updates discoverable, shipped through Drydock's own lifecycle (second dogfood: a verified, archived change packet with a living capability spec).

- **`scripts/release.py` — version lockstep + test-gated releases.** The version is declared in four hand-edited places (`plugin.json`, `marketplace.json`, the operator-guide `VERSION:` line, and the `CHANGELOG` heading) that kept drifting. `release.py <version>` bumps all of them together, refuses on a non-increasing version or missing CHANGELOG notes, runs the test suite + `check_sync`, and prints — never executes — the git publish commands. `release.py --check` detects drift and is wired into CI, so a version mismatch now fails the build. It immediately caught the operator guide, stale at 0.1.3 through four releases.
- **Update-path docs.** README and the operator-guide troubleshooting table now cover the most common "plugin won't update" cause — a stale per-user marketplace clone — with the one-line fix, so users can self-serve.
- **`docs/DEVELOPING.md`.** New maintainer guide: how updates actually reach users, local dev-install (run the plugin from your working tree for instant dogfooding), and the release process.
- **Tests.** `tests/test_release.py` (9 tests; suite now 126), including a negative test proving `release.py` never invokes git.

## 0.1.5 — enforcement-layer hardening (security)

Fixes every high-severity finding from an enforcement-layer audit, shipped through Drydock's own SDD+ lifecycle (its first dogfood: a `PROJECT_CONTEXT.md` plus a verified, synced, archived change packet with living capability specs).

- **Destructive-git hook, rewritten on token parsing.** `git_safety.py` now analyses commands as shell tokens instead of substrings. Closes bypasses via global flags (`git -C .`, `git -c k=v`) and quoted flags, and stops false-positiving on destructive strings quoted inside commit messages. Broadens coverage to `checkout .`/`switch -f`/`restore .` working-tree discards, `+refspec`/`--mirror`/`--delete` pushes, `update-ref -d`, `reflog expire`, and `worktree remove --force`. Honest block message (no phantom "one-time bypass").
- **Secrets hook now covers Bash writes.** `protect_secrets.py` blocks output redirections, `tee`, and `cp`/`mv` into secret paths (previously only Write/Edit), adds modern key types (`id_ed25519`), keystores (`*.p12`/`*.pfx`/`*.jks`), `.envrc`, and `service-account.json`, and stops wrongly blocking `.env.example`/`.template`/`.sample`.
- **Cross-platform hooks.** `hooks.json` invokes `python3 || python`, so the guardrails are no longer silently inert on Windows installs where `python3` is only a Store stub.
- **Deterministic packet gates.** `verify`/`archive` now catch the shipped templates' own placeholder forms (checkbox `- [ ] TBD`, `| TBD |` table cells, a still-`Pending.` Result), match requirement names exactly (no substring false-pass), respect ADDED-section boundaries, and fail closed on a delta spec with no valid `Capability:` line. Fixed the `sdd.ps1` wrapper, which was broken for single-argument commands (`status`, `init`).
- **First test suite and CI.** New `tests/` (117 tests) and GitHub Actions (Ubuntu + Windows × Python 3.9/3.12) running pytest, scaffold-parity, and live guardrail smoke-tests. `check_sync.py` now guards all 10 root↔scaffold pairs (was 1); `.gitattributes` enforces LF so the parity is stable across platforms.

## 0.1.4
- Cross-platform fix: commands and docs now invoke `python3` (with a Windows `python` note) and state an interpreter-resolution rule, instead of bare `python` which dead-ends on modern macOS where no `python` exists. README now documents the Python 3.9+ prerequisite.
- Re-saved README.md as clean UTF-8, fixing mojibake (garbled `⚓`, em-dashes, apostrophes) that showed on the GitHub and marketplace listings.
- Synced the scaffold copies of CLAUDE.md and AGENTS.md with their authoritative versions (the scaffold CLAUDE.md had been shipping stale single-hook documentation to new installs).
- Refreshed stale "0.1.1" version reference in the AI operator guide.

## 0.1.3
- Archive sync gate now checks that a delta's ADDED requirements are actually present in the living capability spec, not merely that the capability file exists. Closes a silent gap where a change could archive with an unsynced delta after the capability's first sync. ADDED requirements only; MODIFIED/REMOVED/RENAMED remain a known limitation.

## 0.1.2
- Fix stale `/sdd:sync` reference in `sdd.py` archive gate → now `/drydock:sync` (both the plugin copy and the distributed scaffold copy).
- `init` now creates `sdd-plus/specs/capabilities/`, the directory the archive gate checks against; previously every delta read as unsynced on fresh installs.
- Move the script-resolution rule out of `status.md` YAML frontmatter into the command body where it takes effect.
- Verifier subagent now checks skill blocking-rules at both the plugin-root and portability-copy paths, instead of assuming `.claude/skills/`.
- Document both PreToolUse hooks (secrets-path and git-safety) in `CLAUDE.md`; previously only secrets protection was mentioned.

## 0.1.1

- Surface the optional LaunchGuardian scanner (`pip install launchguardian`) at first touch: scanner detection in `/drydock:init-project`, a pointer in `/drydock:onboard`'s closing recap, and an availability check in the launchguardian skill before any scan commands.


## 0.1.0 — first public release

- Drydock plugin: 12 governed skills, 9 lifecycle commands, independent `verifier` subagent.
- Safety hooks: secrets-file protection (Write/Edit) and destructive-git guard (Bash).
- `/drydock:init-project` scaffolds the SDD+ project structure into any repo (never overwrites).
- `/drydock:onboard` guided first change.
- Spec lifecycle: delta specs (SHALL + WHEN/THEN) merged into living capability specs via `spec-sync`; gated archive with API blocking rule.
- LaunchGuardian Framework (22 security gates) with templates; companion scanner: `launchguardian-cli`.
- Cross-platform `sdd.py` change-packet tool with placeholder and sync gates.
